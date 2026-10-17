"""Automatic, verifiable quality checks for a rendered poster (uses the layout report)."""
import re

from .render_poster import cmap

MIN_CONTRAST = 4.5        # WCAG AA for normal text
MIN_CONTRAST_LARGE = 3.0  # WCAG AA for large text (>= 4% of poster width here)
IGNORED = set(" \t‌‍")


def _lum(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def check_poster(report: dict, spec: dict) -> tuple[bool, list[str]]:
    notes = []
    w, h, m = report["w"], report["h"], report["margin"]
    safe = 0.04 * w
    if report["overflow"]:
        notes.append("text did not fit at minimum size")
    for b in report["boxes"]:
        x0, y0, x1, y1 = b["box"]
        if x0 < safe or x1 > w - safe or y0 < safe or y1 > h - safe:
            notes.append(f"{b['role']} outside safe margin")
        need = MIN_CONTRAST_LARGE if b["px"] >= 0.04 * w else MIN_CONTRAST
        ratio = contrast(b["fill"], b["behind"])
        if ratio < need:
            notes.append(f"{b['role']} contrast {ratio:.1f} < {need}")
        for run, script in b["scripts"]:
            missing = {c for c in run if c not in IGNORED and ord(c) not in cmap(script)}
            if missing:
                notes.append(f"{b['role']} missing glyphs: {''.join(sorted(missing))}")
    boxes = [b["box"] for b in report["boxes"]]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] - 1 and b[1] < a[3] - 1:
                notes.append("text lines overlap")
    drawn = report["drawn"]
    if spec.get("phone") and _norm(drawn.get("phone")) != _norm(spec["phone"]):
        notes.append("phone number not fully on poster")
    if _norm(drawn.get("offer")) != _norm(spec["offer_text"]):
        notes.append("offer text not fully on poster")
    notes = list(dict.fromkeys(notes))
    return not notes, notes
