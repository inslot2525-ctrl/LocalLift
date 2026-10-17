"""Render every template x size x language without a database and print QA results.
Usage: python -m tests.render_samples OUT_DIR"""
import sys
from pathlib import Path

from pipeline import qa
from pipeline.copywriter import fallback_copy
from pipeline.render_poster import SIZES, TEMPLATES, make_preview, render_with_report

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
out.mkdir(exist_ok=True)
order = {"shop_name": "Sharma Sweets", "phone": "98765 43210", "festival": "diwali",
         "offer_text": "20% off on all sweet boxes above Rs 500"}
offers = {"en": order["offer_text"], "hi": "500 रुपये से ऊपर के सभी मिठाई डिब्बों पर 20% छूट",
          "mr": "500 रुपयांवरील सर्व मिठाई बॉक्सवर 20% सूट"}
failed = 0
for lang in ("en", "hi", "mr"):
    c = fallback_copy({**order, "offer_text": offers[lang]}, lang)
    for t in TEMPLATES:
        for size in SIZES:
            spec = {"shop_name": order["shop_name"], "phone": order["phone"], "offer_text": offers[lang],
                    "headline": c["headline"], "cta": c["cta"], "language": lang, "size": size, "template_id": t}
            png, report = render_with_report(spec)
            ok, notes = qa.check_poster(report, spec)
            failed += not ok
            name = f"{lang}_{t}_{size}"
            (out / f"{name}.png").write_bytes(png)
            if size == "square":
                (out / f"{name}_preview.jpg").write_bytes(make_preview(png))
            print(f"{name:24} {'PASS' if ok else 'FAIL'} {len(png)//1024}KB {'; '.join(notes)}")
# a deliberately long offer must fail the first layout
spec = {**spec, "offer_text": "Mega Diwali dhamaka " * 30}
ok, notes = qa.check_poster(render_with_report(spec)[1], spec)
print("long offer ->", "PASS" if ok else "FAIL", notes)
print("failed:", failed)
