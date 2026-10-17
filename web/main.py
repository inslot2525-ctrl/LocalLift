"""LocalLift web app: landing, order form, preview, UPI payment, downloads, rep links, admin."""
import base64
import io
import logging
import os
import re
import secrets
import time
import zipfile
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlencode

import qrcode
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from PIL import Image

from pipeline.api import trigger_pack
from pipeline.pack import expected_count
from shared.db import apply_schema, connect, log_event

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("web")

LANGUAGES = {"en": "English", "hi": "हिन्दी (Hindi)", "mr": "मराठी (Marathi)"}
FESTIVALS = {"diwali": "Diwali"}
PLANS = {
    "starter": {"name": "Starter pack", "price": int(os.getenv("PRICE_STARTER", "199")), "templates": ["diya"],
                "desc": "1 design in 3 sizes (status, square, A4 print), every language you chose, 3 WhatsApp messages and a review request"},
    "festive_bundle": {"name": "Festive bundle", "price": int(os.getenv("PRICE_BUNDLE", "499")),
                       "templates": ["diya", "rangoli", "lantern"],
                       "desc": "All 3 designs in 3 sizes, every language you chose, all messages. Covers Dhanteras to Bhai Dooj"},
}
SIZE_LABELS = {"status": "WhatsApp status (1080x1920)", "square": "Square post (1080x1080)", "a4": "A4 print (2480x3508)"}
LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_LOGO = 2 * 1024 * 1024
ORDER_LIMIT_PER_HOUR = int(os.getenv("ORDER_LIMIT_PER_HOUR", "8"))
SAMPLE = {"shop_name": "Sharma Sweets (sample)", "phone": "98765 43210", "languages": ["en", "hi"],
          "offer_text": "20% off on all sweet boxes above Rs 500"}

templates = Jinja2Templates(directory=Path(__file__).with_name("templates"))
templates.env.globals.update(LANGUAGES=LANGUAGES, PLANS=PLANS, SIZE_LABELS=SIZE_LABELS)
security = HTTPBasic()
_recent_orders: dict[str, deque] = defaultdict(deque)


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_schema()
    yield


app = FastAPI(title="LocalLift", lifespan=lifespan, docs_url=None, redoc_url=None)


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def rate_limited(ip: str) -> bool:
    q, now = _recent_orders[ip], time.time()
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= ORDER_LIMIT_PER_HOUR:
        return True
    q.append(now)
    return False


def get_order(view_token: str) -> dict:
    with connect() as conn:
        order = conn.execute(
            """select o.id, o.rep_code, o.festival, o.languages, o.offer_text, o.plan, o.amount_inr, o.status,
                      o.payment_ref, o.download_token, o.is_sample, o.view_token, o.created_at,
                      s.name as shop_name, s.phone
               from orders o join shops s on s.id = o.shop_id where o.view_token = %s""",
            (view_token,),
        ).fetchone()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


def item_rows(order_id: int) -> list[dict]:
    with connect() as conn:
        return conn.execute(
            """select id, kind, language, size, template_id, body, qa_status, qa_notes from pack_items
               where order_id = %s order by language, kind, template_id, size""",
            (order_id,),
        ).fetchall()


def create_order(shop_name, phone, offer_text, languages, festival, plan, rep_code, logo, logo_mime, is_sample=False):
    view_token = secrets.token_urlsafe(16)
    with connect() as conn:
        shop = conn.execute("insert into shops (name, phone) values (%s, %s) returning id", (shop_name, phone)).fetchone()
        order = conn.execute(
            """insert into orders (shop_id, rep_code, festival, languages, offer_text, logo, logo_mime, plan,
                                   amount_inr, is_sample, view_token)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
            (shop["id"], rep_code, festival, languages, offer_text, logo, logo_mime, plan,
             PLANS[plan]["price"], is_sample, view_token),
        ).fetchone()
    return order["id"], view_token


# ---------- public pages ----------

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    log_event("visit", meta={"path": "/"})
    return render(request, "landing.html")


@app.get("/r/{code}")
def rep_link(code: str):
    code = code.strip().upper()[:32]
    log_event("visit", rep_code=None, meta={"path": "/r", "rep": code})
    return RedirectResponse(f"/create?rep={quote(code)}", status_code=303)


@app.get("/create", response_class=HTMLResponse)
def create_form(request: Request, rep: str = ""):
    log_event("form_start", meta={"rep": rep[:32]} if rep else None)
    return render(request, "create.html", rep=rep[:32].upper(), form={}, errors=[])


@app.post("/create", response_class=HTMLResponse)
async def create_submit(
    request: Request,
    shop_name: str = Form(""), phone: str = Form(""), offer_text: str = Form(""),
    languages: list[str] = Form([]), festival: str = Form("diwali"), plan: str = Form("starter"),
    rep_code: str = Form(""), logo: UploadFile | None = File(None),
):
    form = {"shop_name": shop_name, "phone": phone, "offer_text": offer_text, "languages": languages, "plan": plan}
    shop_name, offer_text = shop_name.strip(), re.sub(r"[ \t]+", " ", offer_text.strip())
    phone = re.sub(r"[^\d+ ]", "", phone).strip()
    errors = []
    if not 2 <= len(shop_name) <= 50:
        errors.append("Shop name should be 2 to 50 characters.")
    if not 8 <= len(re.sub(r"\D", "", phone)) <= 13:
        errors.append("Enter a valid phone number (it goes on the poster).")
    if not 3 <= len(offer_text) <= 120:
        errors.append("Offer text should be 3 to 120 characters, so it fits on a poster.")
    languages = [l for l in dict.fromkeys(languages) if l in LANGUAGES]
    if not languages:
        errors.append("Pick at least one language.")
    if festival not in FESTIVALS:
        errors.append("Unknown festival.")
    if plan not in PLANS:
        plan = "starter"
    logo_bytes = logo_mime = None
    if logo is not None and logo.filename:
        data = await logo.read(MAX_LOGO + 1)
        if len(data) > MAX_LOGO:
            errors.append("Logo must be under 2 MB.")
        elif logo.content_type not in LOGO_TYPES:
            errors.append("Logo must be a PNG, JPG or WEBP image.")
        else:
            try:
                Image.open(io.BytesIO(data)).verify()
                logo_bytes, logo_mime = data, logo.content_type
            except Exception:
                errors.append("That logo file could not be read as an image.")
    if errors:
        return render(request, "create.html", status_code=400, rep=rep_code, form=form, errors=errors)
    if rate_limited(client_ip(request)):
        return render(request, "create.html", status_code=429, rep=rep_code, form=form,
                      errors=["Too many orders from this connection. Please try again in an hour."])

    rep = None
    code = rep_code.strip().upper()[:32]
    if code:
        with connect() as conn:
            rep = conn.execute("select code from reps where code = %s and active", (code,)).fetchone()
    order_id, view_token = create_order(shop_name, phone, offer_text, languages, festival, plan,
                                        rep["code"] if rep else None, logo_bytes, logo_mime)
    log_event("order_created", order_id, rep["code"] if rep else None,
              {"languages": languages, "plan": plan, "logo": bool(logo_bytes), "rep_given": code or None})
    trigger_pack(order_id)
    return RedirectResponse(f"/o/{view_token}", status_code=303)


@app.get("/sample")
def sample():
    """Demo mode: a fixed sample shop, generated once and reused, never payable."""
    with connect() as conn:
        row = conn.execute("select view_token from orders where is_sample order by id desc limit 1").fetchone()
    if row:
        view_token = row["view_token"]
    else:
        order_id, view_token = create_order(SAMPLE["shop_name"], SAMPLE["phone"], SAMPLE["offer_text"],
                                            SAMPLE["languages"], "diwali", "festive_bundle", None, None, None, True)
        trigger_pack(order_id)
    log_event("sample_view")
    return RedirectResponse(f"/o/{view_token}", status_code=303)


def _order_context(order: dict) -> dict:
    items = item_rows(order["id"])
    expected = expected_count(order)
    posters = [i for i in items if i["kind"] == "poster"]
    messages = [i for i in items if i["kind"] == "message" and i["template_id"] != "headline"]
    return {"order": order, "posters": posters, "messages": messages, "done": len(items) >= expected,
            "progress": len(items), "expected": expected}


@app.get("/o/{view_token}", response_class=HTMLResponse)
def order_page(request: Request, view_token: str):
    return render(request, "order.html", **_order_context(get_order(view_token)))


@app.get("/o/{view_token}/status", response_class=HTMLResponse)
def order_status(request: Request, view_token: str):
    return render(request, "_previews.html", **_order_context(get_order(view_token)))


@app.get("/o/{view_token}/img/{item_id}")
def preview_image(view_token: str, item_id: int):
    order = get_order(view_token)
    with connect() as conn:
        row = conn.execute(
            "select preview_bytes from pack_items where id = %s and order_id = %s and kind = 'poster'",
            (item_id, order["id"]),
        ).fetchone()
    if not row or not row["preview_bytes"]:
        raise HTTPException(404)
    return Response(bytes(row["preview_bytes"]), media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=3600"})


# ---------- payment ----------

def upi_link(amount: int, order_id: int) -> str | None:
    vpa = os.getenv("UPI_VPA")
    if not vpa:
        return None
    params = {"pa": vpa, "pn": os.getenv("UPI_NAME", "LocalLift"), "am": f"{amount}.00", "cu": "INR",
              "tn": f"LocalLift order {order_id}"}
    return "upi://pay?" + urlencode(params, quote_via=quote)


def qr_data_uri(text: str) -> str:
    buf = io.BytesIO()
    qrcode.make(text, box_size=8, border=2).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@app.get("/pay/{view_token}", response_class=HTMLResponse)
def pay_page(request: Request, view_token: str, plan: str = ""):
    order = get_order(view_token)
    if order["is_sample"]:
        return RedirectResponse(f"/o/{view_token}", status_code=303)
    plan = plan if plan in PLANS else order["plan"]
    amount = PLANS[plan]["price"]
    link = upi_link(amount, order["id"])
    if order["status"] == "preview":
        log_event("payment_started", order["id"], order["rep_code"], {"plan": plan})
    return render(request, "pay.html", order=order, plan=plan, amount=amount, upi=link,
                  qr=qr_data_uri(link) if link else None, vpa=os.getenv("UPI_VPA"), error=None)


@app.post("/pay/{view_token}", response_class=HTMLResponse)
def pay_submit(request: Request, view_token: str, plan: str = Form(...), payment_ref: str = Form("")):
    order = get_order(view_token)
    if order["is_sample"] or order["status"] not in ("preview", "awaiting_confirmation", "rejected"):
        return RedirectResponse(f"/o/{view_token}", status_code=303)
    plan = plan if plan in PLANS else "starter"
    ref = re.sub(r"\s", "", payment_ref)[:40]
    if not re.fullmatch(r"[A-Za-z0-9]{6,40}", ref):
        amount = PLANS[plan]["price"]
        link = upi_link(amount, order["id"])
        return render(request, "pay.html", status_code=400, order=order, plan=plan, amount=amount, upi=link,
                      qr=qr_data_uri(link) if link else None, vpa=os.getenv("UPI_VPA"),
                      error="Enter the UPI transaction ID (UTR) from your payment app: letters and numbers only.")
    with connect() as conn:
        conn.execute(
            """update orders set plan = %s, amount_inr = %s, payment_ref = %s, status = 'awaiting_confirmation'
               where id = %s""",
            (plan, PLANS[plan]["price"], ref, order["id"]),
        )
    log_event("payment_submitted", order["id"], order["rep_code"], {"plan": plan})
    return RedirectResponse(f"/o/{view_token}", status_code=303)


# ---------- downloads (paid only) ----------

def paid_order(download_token: str) -> dict:
    with connect() as conn:
        order = conn.execute(
            """select o.id, o.plan, o.languages, o.rep_code, s.name as shop_name from orders o
               join shops s on s.id = o.shop_id where o.download_token = %s and o.status = 'paid'""",
            (download_token,),
        ).fetchone()
    if not order:
        raise HTTPException(404, "Download link not found or not paid yet")
    return order


def unlocked_items(order: dict) -> list[dict]:
    allowed = PLANS[order["plan"]]["templates"]
    return [i for i in item_rows(order["id"])
            if (i["kind"] == "poster" and i["template_id"] in allowed)
            or (i["kind"] == "message" and i["template_id"] != "headline")]


@app.get("/d/{download_token}", response_class=HTMLResponse)
def download_page(request: Request, download_token: str):
    order = paid_order(download_token)
    log_event("download", order["id"], order["rep_code"], {"what": "page"})
    items = unlocked_items(order)
    return render(request, "download.html", order=order, token=download_token,
                  posters=[i for i in items if i["kind"] == "poster"],
                  messages=[i for i in items if i["kind"] == "message"])


def _filename(order: dict, item: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", order["shop_name"].lower()).strip("-")[:30] or "shop"
    return f"{slug}_{item['language']}_{item['template_id']}_{item['size']}.png"


@app.get("/d/{download_token}/file/{item_id}")
def download_file(download_token: str, item_id: int):
    order = paid_order(download_token)
    item = next((i for i in unlocked_items(order) if i["id"] == item_id and i["kind"] == "poster"), None)
    if not item:
        raise HTTPException(404)
    with connect() as conn:
        data = conn.execute("select file_bytes from pack_items where id = %s", (item_id,)).fetchone()["file_bytes"]
    return Response(bytes(data), media_type="image/png",
                    headers={"Content-Disposition": f'attachment; filename="{_filename(order, item)}"'})


@app.get("/d/{download_token}/all.zip")
def download_zip(download_token: str):
    order = paid_order(download_token)
    items = unlocked_items(order)
    buf = io.BytesIO()
    with connect() as conn, zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for item in items:
            if item["kind"] == "poster":
                data = conn.execute("select file_bytes from pack_items where id = %s", (item["id"],)).fetchone()
                zf.writestr(_filename(order, item), bytes(data["file_bytes"]))
        text = "\n\n----------\n\n".join(f"[{i['language']} {i['template_id']}]\n{i['body']}"
                                         for i in items if i["kind"] == "message")
        zf.writestr("messages.txt", text)
    log_event("download", order["id"], order["rep_code"], {"what": "zip"})
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="locallift-pack.zip"'})


# ---------- admin ----------

def admin(creds: HTTPBasicCredentials = Depends(security)) -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise HTTPException(503, "ADMIN_PASSWORD is not set")
    if not (secrets.compare_digest(creds.username, os.getenv("ADMIN_USER", "admin"))
            and secrets.compare_digest(creds.password, password)):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    return creds.username


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, _: str = Depends(admin)):
    with connect() as conn:
        orders = conn.execute(
            """select o.id, o.status, o.plan, o.amount_inr, o.payment_ref, o.rep_code, o.is_sample, o.languages,
                      o.created_at, o.view_token, s.name as shop_name, s.phone,
                      (select count(*) from pack_items p where p.order_id = o.id) as items,
                      (select count(*) from pack_items p where p.order_id = o.id and p.qa_status = 'failed') as failed
               from orders o join shops s on s.id = o.shop_id order by o.id desc limit 200"""
        ).fetchall()
        ledger = conn.execute(
            """select l.*, r.name as rep_name, r.upi_id from ledger l join reps r on r.code = l.rep_code
               order by l.id desc limit 200"""
        ).fetchall()
        reps = conn.execute(
            """select r.*, coalesce(sum(l.amount_inr) filter (where l.status <> 'paid_out'), 0) as owed,
                      count(l.id) as sales
               from reps r left join ledger l on l.rep_code = r.code group by r.code order by r.created_at"""
        ).fetchall()
    return render(request, "admin.html", orders=orders, ledger=ledger, reps=reps, funnel=funnel_counts())


@app.get("/admin/orders/{order_id}", response_class=HTMLResponse)
def admin_order(request: Request, order_id: int, _: str = Depends(admin)):
    with connect() as conn:
        vt = conn.execute("select view_token from orders where id = %s", (order_id,)).fetchone()
    if not vt:
        raise HTTPException(404)
    ctx = _order_context(get_order(vt["view_token"]))
    return render(request, "admin_order.html", **ctx)


@app.post("/admin/orders/{order_id}/approve")
def admin_approve(order_id: int, _: str = Depends(admin)):
    with connect() as conn:
        with conn.transaction():
            order = conn.execute(
                """update orders set status = 'paid', paid_at = now(), download_token = %s
                   where id = %s and status = 'awaiting_confirmation' and not is_sample
                   returning id, rep_code, amount_inr""",
                (secrets.token_urlsafe(24), order_id),
            ).fetchone()
            if order and order["rep_code"]:
                rep = conn.execute("select commission_pct from reps where code = %s and active",
                                   (order["rep_code"],)).fetchone()
                if rep:
                    conn.execute(
                        """insert into ledger (order_id, rep_code, amount_inr) values (%s, %s, %s)
                           on conflict (order_id) do nothing""",
                        (order_id, order["rep_code"], order["amount_inr"] * rep["commission_pct"] // 100),
                    )
    if order:
        log_event("paid", order_id, order["rep_code"], {"amount": order["amount_inr"]})
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/orders/{order_id}/reject")
def admin_reject(order_id: int, _: str = Depends(admin)):
    with connect() as conn:
        conn.execute("update orders set status = 'rejected' where id = %s and status = 'awaiting_confirmation'",
                     (order_id,))
    log_event("payment_rejected", order_id)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/ledger/{ledger_id}/{action}")
def admin_ledger(ledger_id: int, action: str, _: str = Depends(admin)):
    transitions = {"approve": ("pending", "approved"), "paid": ("approved", "paid_out")}
    if action not in transitions:
        raise HTTPException(400)
    before, after = transitions[action]
    with connect() as conn:
        conn.execute("update ledger set status = %s where id = %s and status = %s", (after, ledger_id, before))
    return RedirectResponse("/admin#ledger", status_code=303)


@app.post("/admin/reps")
def admin_add_rep(code: str = Form(...), name: str = Form(...), upi_id: str = Form(""),
                  commission_pct: int = Form(30), _: str = Depends(admin)):
    code = re.sub(r"[^A-Z0-9]", "", code.upper())[:16]
    if not code or not name.strip() or not 0 <= commission_pct <= 100:
        raise HTTPException(400, "Code, name and a 0-100 commission are required")
    with connect() as conn:
        conn.execute(
            """insert into reps (code, name, upi_id, commission_pct) values (%s, %s, %s, %s)
               on conflict (code) do update set name = excluded.name, upi_id = excluded.upi_id,
               commission_pct = excluded.commission_pct""",
            (code, name.strip()[:60], upi_id.strip()[:60] or None, commission_pct),
        )
    return RedirectResponse("/admin#reps", status_code=303)


@app.post("/admin/reps/{code}/toggle")
def admin_toggle_rep(code: str, _: str = Depends(admin)):
    with connect() as conn:
        conn.execute("update reps set active = not active where code = %s", (code,))
    return RedirectResponse("/admin#reps", status_code=303)


FUNNEL = ["visit", "form_start", "order_created", "preview_ready", "payment_started", "payment_submitted", "paid", "download"]


def funnel_counts() -> list[dict]:
    """Counts exclude sample orders. visit/form_start are page loads; the rest are distinct orders."""
    with connect() as conn:
        rows = conn.execute(
            """select e.kind, count(*) as events, count(distinct e.order_id) as orders
               from events e left join orders o on o.id = e.order_id
               where coalesce(o.is_sample, false) = false group by e.kind"""
        ).fetchall()
    by_kind = {r["kind"]: r for r in rows}
    return [{"kind": k, "events": by_kind.get(k, {}).get("events", 0), "orders": by_kind.get(k, {}).get("orders", 0)}
            for k in FUNNEL]


@app.get("/admin/funnel", response_class=HTMLResponse)
def admin_funnel(request: Request, _: str = Depends(admin)):
    return render(request, "admin_funnel.html", funnel=funnel_counts())
