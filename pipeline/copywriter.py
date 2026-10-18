"""Copy for a pack: poster headline + CTA, three WhatsApp messages and one review request per language.

An LLM writes the copy when LLM_PROVIDER=anthropic and LLM_API_KEY are set. Any failure or invalid
output falls back, per language, to the human-written library in copy_library/<festival>.json.
"""
import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger(__name__)

LIBRARY_DIR = Path(__file__).with_name("copy_library")
LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
THEMES = {"diwali": "Diwali", "offer": "special"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def library(festival: str) -> dict:
    return json.loads((LIBRARY_DIR / f"{festival}.json").read_text(encoding="utf-8"))


def _fill(text: str, order: dict) -> str:
    return text.format(shop=order["shop_name"], offer=order["offer_text"], phone=order["phone"] or "")


def fallback_copy(order: dict, language: str) -> dict:
    lib = library(order["festival"])[language]
    return {
        "headline": lib["headline"],
        "cta": lib["cta"],
        "whatsapp": [_fill(m, order) for m in lib["whatsapp"]],
        "review": _fill(lib["review"], order),
        "source": "library",
    }


def _valid(lang: str, c: dict) -> bool:
    try:
        texts = [c["headline"], c["review"], *c["whatsapp"]]
    except (KeyError, TypeError):
        return False
    if len(c["whatsapp"]) != 3 or not all(isinstance(t, str) and t.strip() for t in texts):
        return False
    if len(c["headline"]) > 40 or any(len(t) > 600 for t in texts):
        return False
    if lang in ("hi", "mr") and not all(DEVANAGARI.search(t) for t in texts):
        return False
    return True


def _ensure_phone(text: str, phone: str) -> str:
    return text if not phone or phone in text else f"{text}\n📞 {phone}"


def _llm_copy(order: dict, languages: list[str]) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["LLM_API_KEY"], timeout=40, max_retries=1)
    langs = ", ".join(f"{code} ({LANG_NAMES[code]})" for code in languages)
    prompt = (
        f"You write short marketing copy for a small Indian shop's {THEMES.get(order['festival'], 'special')} offer.\n"
        f"Shop: {order['shop_name']}\nOffer: {order['offer_text']}\nPhone: {order['phone']}\n\n"
        f"For each language in [{langs}], write natural, warm, everyday copy (not formal or literary) with:\n"
        "- headline: a short poster headline of at most 30 characters that fits the occasion\n"
        "- whatsapp: exactly 3 different broadcast messages (under 350 characters each) that state the offer "
        "and the phone number; one or two emoji is fine\n"
        "- review: one polite message asking a customer to leave a Google review\n"
        "Never invent discounts, prices or claims beyond the offer given. Hindi and Marathi must be in Devanagari.\n"
        'Reply with only JSON: {"<code>": {"headline": "...", "whatsapp": ["...", "...", "..."], "review": "..."}}'
    )
    resp = client.messages.create(
        model=os.getenv("LLM_MODEL", "claude-opus-5-5"),
        max_tokens=4000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason != "end_turn":
        raise ValueError(f"LLM stopped with {resp.stop_reason}")
    text = "".join(b.text for b in resp.content if b.type == "text")
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON in LLM reply")
    return json.loads(match.group(0))


def generate_copy(order: dict) -> dict:
    """order needs shop_name, phone, offer_text, festival, languages. Returns {language: copy dict}."""
    languages = list(order["languages"])
    llm = {}
    if os.getenv("LLM_PROVIDER") == "anthropic" and os.getenv("LLM_API_KEY"):
        try:
            llm = _llm_copy(order, languages)
        except Exception as exc:  # any failure -> library copy
            log.warning("LLM copy failed, using library: %s", exc)
    out = {}
    for lang in languages:
        fallback = fallback_copy(order, lang)
        c = llm.get(lang)
        if c and _valid(lang, c):
            out[lang] = {
                "headline": c["headline"].strip(),
                "cta": fallback["cta"],
                "whatsapp": [_ensure_phone(m.strip(), order["phone"]) for m in c["whatsapp"]],
                "review": c["review"].strip(),
                "source": "llm",
            }
        else:
            out[lang] = fallback
    return out
