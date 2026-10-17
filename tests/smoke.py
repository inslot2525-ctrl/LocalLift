"""End-to-end smoke test against a running app (local compose stack or the live URL).

Usage: python tests/smoke.py BASE_URL ADMIN_PASSWORD
Walks: landing -> rep -> order -> previews -> pay -> admin approve -> ledger -> download -> funnel.
Creates a real order row; on the live site, reject or delete it afterwards (it uses phone 90000 00000).
"""
import re
import sys
import time

import httpx

base, password = sys.argv[1].rstrip("/"), sys.argv[2]
c = httpx.Client(base_url=base, timeout=60, follow_redirects=False)
admin = (("admin", password))


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


check(c.get("/").status_code == 200, "landing")
check(c.get("/admin").status_code == 401, "admin needs a password")
r = c.post("/admin/reps", auth=admin, data={"code": "SMOKE", "name": "Smoke Test Rep", "upi_id": "smoke@upi", "commission_pct": 30})
check(r.status_code == 303, "create rep")
r = c.get("/r/smoke")
check(r.status_code == 303 and "rep=SMOKE" in r.headers["location"], "rep link prefills code")

bad = c.post("/create", data={"shop_name": "", "phone": "12", "offer_text": "", "languages": []})
check(bad.status_code == 400 and "Shop name" in bad.text, "form validation")

r = c.post("/create", data={"shop_name": "Smoke Test Store", "phone": "90000 00000", "offer_text": "Flat 10% off this Diwali",
                            "languages": ["en", "hi"], "plan": "starter", "rep_code": "SMOKE", "festival": "diwali"})
check(r.status_code == 303 and r.headers["location"].startswith("/o/"), "order created")
order_url = r.headers["location"]
vt = order_url.split("/")[-1]

t0 = time.time()
while time.time() - t0 < 240:
    s = c.get(f"{order_url}/status").text
    if "Making your pack" not in s:
        break
    time.sleep(2)
check("Making your pack" not in s, f"pack generated in {time.time() - t0:.0f}s")
imgs = re.findall(rf"/o/{vt}/img/(\d+)", s)
check(len(imgs) >= 6, f"{len(imgs)} preview images listed")
img = c.get(f"/o/{vt}/img/{imgs[0]}")
check(img.status_code == 200 and img.headers["content-type"] == "image/jpeg", "preview image served")
check(c.get(f"/o/{vt}/img/999999").status_code == 404, "foreign item id rejected")

check(c.get(f"/pay/{vt}?plan=festive_bundle").status_code == 200, "pay page")
check(c.post(f"/pay/{vt}", data={"plan": "festive_bundle", "payment_ref": "x"}).status_code == 400, "bad UTR rejected")
r = c.post(f"/pay/{vt}", data={"plan": "festive_bundle", "payment_ref": "SMOKE123456"})
check(r.status_code == 303, "payment reference submitted")

home = c.get("/admin", auth=admin).text
oid = re.search(r'/admin/orders/(\d+)/approve', home).group(1)
check(c.post(f"/admin/orders/{oid}/approve", auth=admin).status_code == 303, f"admin approved order {oid}")
check(c.post(f"/admin/orders/{oid}/approve", auth=admin).status_code == 303, "second approve is harmless")
page = c.get(order_url).text
token = re.search(r"/d/([\w-]+)", page)
check(token is not None, "download link on order page")
d = c.get(f"/d/{token.group(1)}")
check(d.status_code == 200 and d.text.count("/file/") == 3 * 3 * 2, "bundle unlocks 3 designs x 3 sizes x 2 languages")
f = c.get(re.search(rf"/d/{token.group(1)}/file/\d+", d.text).group(0))
check(f.status_code == 200 and f.content[:4] == b"\x89PNG", "clean PNG download")
z = c.get(f"/d/{token.group(1)}/all.zip")
check(z.status_code == 200 and z.content[:2] == b"PK", "zip download")
home = c.get("/admin", auth=admin).text
check("Smoke Test Rep (SMOKE)" in home and ">149<" in home, "ledger row: 30% of 499 = 149")
fun = c.get("/admin/funnel", auth=admin).text
check("paid" in fun, "funnel page")
check(c.get("/sample").status_code == 303, "sample mode")
print("ALL OK")
