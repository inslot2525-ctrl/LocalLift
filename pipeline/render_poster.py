"""Poster rendering with Pillow + RAQM (needs libfribidi at runtime; see Dockerfile).

render_item(spec) -> PNG bytes. render_with_report(spec) also returns a layout report that
qa.check_poster uses (text boxes, colours behind each box, overflow flags, fonts used per run).
Templates are drawn from simple shapes only: no external art.
"""
import io
import math
import random
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageStat, features

FONT_DIR = Path(__file__).with_name("fonts")
SIZES = {"square": (1080, 1080), "status": (1080, 1920), "a4": (2480, 3508)}
TEMPLATES = ("diya", "rangoli", "lantern")
LAYOUT = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC

PALETTES = {
    "diya": dict(bg=(74, 14, 30), bg2=(128, 28, 44), accent=(247, 186, 64), text=(255, 242, 214),
                 offer_bg=(247, 186, 64), offer_text=(64, 10, 24)),
    "rangoli": dict(bg=(255, 246, 228), bg2=(255, 234, 204), accent=(196, 32, 80), text=(58, 18, 40),
                    offer_bg=(196, 32, 80), offer_text=(255, 255, 255), petals=[(196, 32, 80), (0, 128, 128), (240, 150, 20)]),
    "lantern": dict(bg=(16, 26, 66), bg2=(34, 48, 108), accent=(255, 150, 50), text=(255, 238, 206),
                    offer_bg=(255, 150, 50), offer_text=(16, 26, 66)),
    "simple": dict(bg=(255, 255, 255), bg2=(255, 255, 255), accent=(176, 24, 48), text=(24, 24, 24),
                   offer_bg=(176, 24, 48), offer_text=(255, 255, 255)),
}


# ---------- fonts and mixed-script text ----------

def _font_path(script: str, bold: bool) -> Path:
    family = "NotoSansDevanagari" if script == "deva" else "NotoSans"
    return FONT_DIR / f"{family}-{'Bold' if bold else 'Regular'}.ttf"


@lru_cache(maxsize=None)
def font(script: str, bold: bool, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_font_path(script, bold)), size, layout_engine=LAYOUT)


@lru_cache(maxsize=None)
def cmap(script: str) -> frozenset:
    return frozenset(TTFont(str(_font_path(script, True)), lazy=True).getBestCmap())


def _is_deva(ch: str) -> bool:
    return "ऀ" <= ch <= "ॿ" or "꣠" <= ch <= "ꣿ"


def segments(text: str) -> list[tuple[str, str]]:
    """Split text into (run, script) pairs. Neutral characters (spaces, digits, punctuation)
    stay with the current run when its font has them, so shaping is not broken up."""
    runs: list[list] = []
    for ch in text:
        if _is_deva(ch) or ch in "‌‍":
            script = "deva"
        elif ch.isalpha():
            script = "latin"
        else:
            cur = runs[-1][1] if runs else "latin"
            script = cur if ord(ch) in cmap(cur) else ("latin" if ord(ch) in cmap("latin") else cur)
        if runs and runs[-1][1] == script:
            runs[-1][0] += ch
        else:
            runs.append([ch, script])
    return [(t, s) for t, s in runs]


def text_width(text: str, size: int, bold: bool) -> float:
    return sum(font(s, bold, size).getlength(t) for t, s in segments(text))


def draw_line(draw: ImageDraw.ImageDraw, x: float, baseline: float, text: str, size: int, bold: bool, fill) -> None:
    for t, s in segments(text):
        f = font(s, bold, size)
        draw.text((x, baseline), t, font=f, fill=fill, anchor="ls")
        x += f.getlength(t)


def wrap(text: str, size: int, bold: bool, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if cur and text_width(trial, size, bold) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
    return lines


# ---------- backgrounds and decorations ----------

def _gradient(w: int, h: int, top, bottom) -> Image.Image:
    col = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        col.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return col.resize((w, h), Image.BILINEAR)


def _star(draw, cx, cy, r, fill):
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i
        rad = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def _petal(cx, cy, length, width, angle):
    pts = []
    for i in range(24):
        t = math.pi * 2 * i / 24
        x, y = length / 2 * math.cos(t) + length / 2, width / 2 * math.sin(t)
        pts.append((cx + x * math.cos(angle) - y * math.sin(angle), cy + x * math.sin(angle) + y * math.cos(angle)))
    return pts


def _rangoli(draw, cx, cy, r, colours):
    for ring, (count, scale) in enumerate([(16, 1.0), (12, 0.68), (8, 0.4)]):
        col = colours[ring % len(colours)]
        for i in range(count):
            draw.polygon(_petal(cx, cy, r * scale, r * scale * 0.32, 2 * math.pi * i / count + ring * 0.2), fill=col)
    draw.ellipse((cx - r * 0.14, cy - r * 0.14, cx + r * 0.14, cy + r * 0.14), fill=colours[0])


def _diya(layer_draw, cx, base, s):
    """A clay lamp: bowl, flame and a soft glow."""
    layer_draw.ellipse((cx - 45 * s, base - 120 * s, cx + 45 * s, base - 30 * s), fill=(255, 200, 80, 28))
    layer_draw.pieslice((cx - 60 * s, base - 70 * s, cx + 60 * s, base + 10 * s), 0, 180, fill=(196, 90, 30, 255))
    layer_draw.ellipse((cx - 13 * s, base - 78 * s, cx + 13 * s, base - 30 * s), fill=(255, 210, 60, 255))
    layer_draw.ellipse((cx - 6 * s, base - 60 * s, cx + 6 * s, base - 36 * s), fill=(255, 250, 220, 255))


def _lantern(layer_draw, cx, top, s, colour):
    layer_draw.line((cx, 0, cx, top), fill=(255, 220, 160, 255), width=max(2, int(3 * s)))
    layer_draw.ellipse((cx - 90 * s, top - 10 * s, cx + 90 * s, top + 190 * s), fill=colour[:3] + (50,))
    layer_draw.rectangle((cx - 28 * s, top, cx + 28 * s, top + 18 * s), fill=(230, 180, 60, 255))
    layer_draw.rounded_rectangle((cx - 50 * s, top + 16 * s, cx + 50 * s, top + 156 * s), radius=int(40 * s), fill=colour)
    layer_draw.rectangle((cx - 28 * s, top + 154 * s, cx + 28 * s, top + 170 * s), fill=(230, 180, 60, 255))
    for dx in (-22, 0, 22):
        layer_draw.line((cx + dx * s, top + 22 * s, cx + dx * s, top + 150 * s), fill=(255, 230, 170, 160), width=max(1, int(2 * s)))


def draw_background(template: str, w: int, h: int, seed: int) -> tuple[Image.Image, dict]:
    """Returns the decorated background and the band (top, bottom) left free for text."""
    p = PALETTES[template]
    s = w / 1080
    img = _gradient(w, h, p["bg"], p["bg2"]).convert("RGBA")
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(seed)
    top, bottom = 0.06 * h, 0.94 * h
    if template == "diya":
        inset = 28 * s
        d.rectangle((inset, inset, w - inset, h - inset), outline=p["accent"] + (255,), width=max(2, int(4 * s)))
        for _ in range(int(26 * (h / w))):
            _star(d, rnd.uniform(0.05, 0.95) * w, rnd.uniform(0.04, 0.5) * h, rnd.uniform(5, 13) * s, (255, 226, 150, 150))
        n = 5
        base = h - 50 * s
        for i in range(n):
            _diya(d, w * (i + 0.5) / n, base, s)
        bottom = h - 180 * s
    elif template == "rangoli":
        r = 0.26 * w
        for cx, cy in [(0, 0), (w, 0), (0, h), (w, h)]:
            _rangoli(d, cx, cy, r, p["petals"])
        top, bottom = 0.5 * r + 0.04 * h, h - 0.5 * r - 0.04 * h
    elif template == "lantern":
        for _ in range(int(40 * (h / w))):
            _star(d, rnd.uniform(0, 1) * w, rnd.uniform(0, 1) * h, rnd.uniform(3, 9) * s, (255, 240, 200, 120))
        colours = [(232, 72, 52, 255), (255, 150, 50, 255), (210, 40, 90, 255)]
        for i, fx in enumerate((0.14, 0.86)):
            _lantern(d, fx * w, (60 + 50 * i) * s, s, colours[i])
        top = 0.06 * h + 240 * s
    img = Image.alpha_composite(img, layer).convert("RGB")
    return img, {"top": top, "bottom": bottom}


# ---------- layout ----------

def _blocks(spec: dict, p: dict) -> list[dict]:
    return [
        {"role": "shop", "text": spec["shop_name"], "bold": True, "size": 0.075, "min": 0.04, "lines": 2, "fill": p["text"]},
        {"role": "headline", "text": spec["headline"], "bold": True, "size": 0.085, "min": 0.045, "lines": 2, "fill": p["accent"]},
        {"role": "offer", "text": spec["offer_text"], "bold": True, "size": 0.07, "min": 0.038, "lines": 4, "fill": p["offer_text"], "box": p["offer_bg"]},
        {"role": "cta", "text": spec["cta"], "bold": False, "size": 0.045, "min": 0.03, "lines": 1, "fill": p["text"]},
        {"role": "phone", "text": spec["phone"], "bold": True, "size": 0.065, "min": 0.04, "lines": 1, "fill": p["accent"]},
    ]


def _plan(blocks, w, max_w, avail_h, logo_h, k):
    """Wrap every block at scale k. Returns (planned blocks, total height, overflow)."""
    planned, total, overflow = [], logo_h, False
    for b in blocks:
        if not b["text"]:
            continue
        inner = max_w - (0.08 * w if "box" in b else 0)
        size = int(max(b["size"] * k, b["min"]) * w)
        while True:
            lines = wrap(b["text"], size, b["bold"], inner)
            fits = len(lines) <= b["lines"] and all(text_width(l, size, b["bold"]) <= inner for l in lines)
            if fits or size <= b["min"] * w:
                break
            size = int(size * 0.92)
        if not fits:
            overflow = True
        line_h = size * 1.5
        pad = 0.035 * w if "box" in b else 0
        h = line_h * len(lines) + 2 * pad
        planned.append({**b, "px": size, "wrapped": lines, "line_h": line_h, "pad": pad, "h": h})
        total += h + 0.03 * w
    return planned, total, overflow or total > avail_h


def render_with_report(spec: dict) -> tuple[bytes, dict]:
    template = spec["template_id"] if spec.get("layout") != "simple" else "simple"
    w, h = SIZES[spec["size"]]
    p = PALETTES[template]
    seed = sum(map(ord, spec["shop_name"])) + w
    if template == "simple":
        bg = Image.new("RGB", (w, h), p["bg"])
        band = {"top": 0.06 * h, "bottom": 0.94 * h}
    else:
        bg, band = draw_background(template, w, h, seed)
    margin = 0.07 * w
    max_w = w - 2 * margin
    avail_h = band["bottom"] - band["top"]

    logo = None
    if spec.get("logo"):
        try:
            logo = Image.open(io.BytesIO(spec["logo"])).convert("RGBA")
            logo.thumbnail((int(0.35 * w), int(min(0.12 * h, 0.16 * w))))
        except Exception:
            logo = None
    logo_h = logo.height + 0.03 * w if logo else 0

    blocks = _blocks(spec, p)
    k = 1.0
    planned, total, overflow = _plan(blocks, w, max_w, avail_h, logo_h, k)
    while overflow and k > 0.55:
        k -= 0.08
        planned, total, overflow = _plan(blocks, w, max_w, avail_h, logo_h, k)

    img = bg.copy()
    draw = ImageDraw.Draw(img)
    y = band["top"] + max(0, (avail_h - total) / 2)
    report = {"w": w, "h": h, "margin": margin, "overflow": overflow, "boxes": [], "template": template}
    if logo:
        img.paste(logo, (int((w - logo.width) / 2), int(y)), logo)
        y += logo_h
    for b in planned:
        if "box" in b:
            bx0, bx1 = margin, w - margin
            draw.rounded_rectangle((bx0, y, bx1, y + b["h"]), radius=int(0.03 * w), fill=b["box"])
        ty = y + b["pad"]
        for line in b["wrapped"]:
            lw = text_width(line, b["px"], b["bold"])
            x = (w - lw) / 2
            box = (x, ty, x + lw, ty + b["line_h"])
            behind = b["box"] if "box" in b else tuple(int(v) for v in ImageStat.Stat(bg.crop(tuple(map(int, box)))).mean[:3])
            draw_line(draw, x, ty + b["px"] * 1.12, line, b["px"], b["bold"], b["fill"])
            report["boxes"].append({
                "role": b["role"], "text": line, "box": box, "px": b["px"], "fill": b["fill"], "behind": behind,
                "scripts": segments(line),
            })
            ty += b["line_h"]
        y += b["h"] + 0.03 * w
    report["drawn"] = {b["role"]: " ".join(b["wrapped"]) for b in planned}
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=spec["size"] != "a4")
    return buf.getvalue(), report


def render_item(spec: dict) -> bytes:
    return render_with_report(spec)[0]


def make_preview(png: bytes, width: int = 540) -> bytes:
    """Low-resolution JPEG with a repeated diagonal 'PREVIEW - LocalLift' watermark."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
    side = int(math.hypot(*img.size)) + 40
    mark = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(mark)
    f = font("latin", True, max(18, width // 16))
    label = "PREVIEW - LocalLift   "
    step = int(f.size * 2.6)
    for row, yy in enumerate(range(0, side, step)):
        d.text((-(row % 2) * step, yy), label * 8, font=f, fill=(255, 255, 255, 110), stroke_width=2, stroke_fill=(0, 0, 0, 90))
    mark = mark.rotate(30, resample=Image.BICUBIC)
    left, top = (side - img.width) // 2, (side - img.height) // 2
    mark = mark.crop((left, top, left + img.width, top + img.height))
    out = Image.alpha_composite(img.convert("RGBA"), mark).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=72)
    return buf.getvalue()
