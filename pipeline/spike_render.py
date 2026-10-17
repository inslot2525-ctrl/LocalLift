"""Rendering spike: check Devanagari shaping with Pillow + RAQM. Writes spike.png."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

FONT = Path(__file__).parent / "fonts" / "NotoSansDevanagari-Bold.ttf"
LINES = [
    "दीपावली की हार्दिक शुभकामनाएँ",
    "दिवाळीच्या हार्दिक शुभेच्छा",
    "Happy Diwali - 20% off",
]


def main(out: str = "spike.png") -> None:
    raqm = features.check("raqm")
    print("pillow raqm:", raqm, "fribidi:", features.version("fribidi"), "harfbuzz:", features.version("harfbuzz"))
    engine = ImageFont.Layout.RAQM if raqm else ImageFont.Layout.BASIC
    font = ImageFont.truetype(str(FONT), 64, layout_engine=engine)
    img = Image.new("RGB", (1080, 400), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(LINES):
        draw.text((40, 40 + i * 110), line, font=font, fill="black")
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
