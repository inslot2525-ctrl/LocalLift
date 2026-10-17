"""Pack generation steps. Each step is idempotent: work already recorded for the same
(order, kind, language, size, template) is skipped, so any step can be retried or re-run safely.

Used by the Render Workflows tasks (workflow.py) and by the local runner (run_pack_locally).
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from shared.db import connect, log_event

from . import qa
from .copywriter import fallback_copy, generate_copy
from .render_poster import SIZES, TEMPLATES, make_preview, render_with_report

log = logging.getLogger(__name__)
MESSAGE_SLOTS = ("wa1", "wa2", "wa3", "review", "headline")  # headline is stored so re-runs reuse it


def load_order(order_id: int) -> dict:
    with connect() as conn:
        order = conn.execute(
            """select o.*, s.name as shop_name, s.phone from orders o join shops s on s.id = o.shop_id
               where o.id = %s""",
            (order_id,),
        ).fetchone()
    if not order:
        raise ValueError(f"order {order_id} not found")
    return order


def item_specs(order: dict) -> list[tuple[str, str, str]]:
    """(language, size, template) for every poster in the preview. All templates are rendered so the
    shop sees the full bundle; the plan decides what the download unlocks."""
    return [(lang, size, t) for lang in order["languages"] for t in TEMPLATES for size in SIZES]


def expected_count(order: dict) -> int:
    return len(item_specs(order)) + len(order["languages"]) * len(MESSAGE_SLOTS)


def write_copy(order_id: int) -> dict:
    """Generate messages once and store them; return {language: {headline, cta}} for the posters."""
    order = load_order(order_id)
    with connect() as conn:
        have = conn.execute(
            "select language, body from pack_items where order_id = %s and kind = 'message' and template_id = 'headline'",
            (order_id,),
        ).fetchall()
    stored = {r["language"]: r["body"] for r in have}
    if all(lang in stored for lang in order["languages"]):
        return {lang: {"headline": stored[lang], "cta": fallback_copy(order, lang)["cta"]} for lang in order["languages"]}
    copy = generate_copy(order)
    with connect() as conn:
        for lang, c in copy.items():
            for slot, body in zip(MESSAGE_SLOTS, [*c["whatsapp"], c["review"], c["headline"]]):
                ok = slot == "headline" or (bool(order["phone"]) and order["phone"] in body)
                conn.execute(
                    """insert into pack_items (order_id, kind, language, size, template_id, body, mime, qa_status, qa_notes)
                       values (%s, 'message', %s, '', %s, %s, 'text/plain', %s, %s)
                       on conflict (order_id, kind, language, size, template_id) do nothing""",
                    (order_id, lang, slot, body, "passed" if ok else "failed",
                     f"source: {c['source']}" + ("" if ok else "; phone number missing")),
                )
    return {lang: {"headline": c["headline"], "cta": c["cta"]} for lang, c in copy.items()}


def render_one(order_id: int, language: str, size: str, template_id: str, headline: str, cta: str) -> dict:
    """Render one poster, check it, retry once with the simple layout if checks fail, store it."""
    with connect() as conn:
        done = conn.execute(
            """select qa_status from pack_items where order_id = %s and kind = 'poster'
               and language = %s and size = %s and template_id = %s""",
            (order_id, language, size, template_id),
        ).fetchone()
    if done:
        return {"skipped": True, "qa_status": done["qa_status"]}
    order = load_order(order_id)
    spec = {
        "shop_name": order["shop_name"], "phone": order["phone"] or "", "offer_text": order["offer_text"],
        "headline": headline, "cta": cta, "language": language, "size": size, "template_id": template_id,
        "logo": bytes(order["logo"]) if order["logo"] else None,
    }
    png, report = render_with_report(spec)
    passed, notes = qa.check_poster(report, spec)
    if not passed:
        first = notes
        png, report = render_with_report({**spec, "layout": "simple"})
        passed, notes = qa.check_poster(report, spec)
        notes = [f"first layout failed ({'; '.join(first)}); used simple layout"] + notes
    with connect() as conn:
        conn.execute(
            """insert into pack_items (order_id, kind, language, size, template_id, mime, file_bytes, preview_bytes, qa_status, qa_notes)
               values (%s, 'poster', %s, %s, %s, 'image/png', %s, %s, %s, %s)
               on conflict (order_id, kind, language, size, template_id) do nothing""",
            (order_id, language, size, template_id, png, make_preview(png),
             "passed" if passed else "failed", "; ".join(notes) or None),
        )
    return {"skipped": False, "qa_status": "passed" if passed else "failed", "notes": notes}


def bundle_pack(order_id: int) -> dict:
    """Pack-level audit: every expected item exists; record preview_ready once."""
    order = load_order(order_id)
    with connect() as conn:
        rows = conn.execute(
            "select qa_status, count(*) as n from pack_items where order_id = %s group by qa_status", (order_id,)
        ).fetchall()
        counts = {r["qa_status"]: r["n"] for r in rows}
        already = conn.execute(
            "select 1 from events where kind = 'preview_ready' and order_id = %s", (order_id,)
        ).fetchone()
    total = sum(counts.values())
    summary = {"order_id": order_id, "expected": expected_count(order), "total": total, **counts}
    if not already and total >= summary["expected"]:
        log_event("preview_ready", order_id, order["rep_code"], summary)
    return summary


def run_pack_locally(order_id: int, workers: int = 3) -> dict:
    """Fallback when Render Workflows is not configured: same steps, in a thread pool."""
    try:
        order = load_order(order_id)
        copy = write_copy(order_id)
        with ThreadPoolExecutor(workers) as pool:
            futures = [
                pool.submit(render_one, order_id, lang, size, t, copy[lang]["headline"], copy[lang]["cta"])
                for lang, size, t in item_specs(order)
            ]
            for f in futures:
                f.result()
        return bundle_pack(order_id)
    except Exception:
        log.exception("local pack run failed for order %s", order_id)
        raise
