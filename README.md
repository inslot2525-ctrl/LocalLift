# LocalLift

Done-for-you festive marketing packs (offer posters, WhatsApp messages, review requests) for small local shops, in their own language. Student reps sell and set up packs and earn a commission on each confirmed sale. v1: Diwali offer packs.

Built for RevHack 2026. Team docs: `CLAUDE.md`, `ROADMAP.md`, `BRIEF_*.md`, `SUBMISSION.md`.

- Live URL: [TODO]
- How packs are made and how we use Render Workflows: [`pipeline/README.md`](pipeline/README.md)

## Pages

| Path | What |
|---|---|
| `/` | Landing page |
| `/create` | 60-second order form (free watermarked preview) |
| `/o/{token}` | Order page: live progress, previews, pay button, download link once paid |
| `/pay/{token}` | Plan choice, UPI deep link + QR, payment reference (UTR) |
| `/d/{token}` | Clean downloads (paid orders only), ZIP, copy / send-on-WhatsApp buttons |
| `/r/{CODE}` | Rep referral link (prefills the rep code) |
| `/sample` | Demo order for a made-up shop, never payable |
| `/admin` | Approve/reject payments, commission ledger, reps (HTTP basic auth) |
| `/admin/funnel` | Funnel counts from the `events` table, samples excluded |

## Run locally

```
docker compose up --build              # app on http://localhost:8000, admin password "localadmin"
python tests/smoke.py http://localhost:8000 localadmin
```

Rendering needs Linux + `libfribidi0` (see `pipeline/README.md`), so run it through Docker; Hindi and Marathi render wrongly with Pillow on Windows.

## Deploy on Render

1. **Blueprint:** Render Dashboard → New → Blueprint → this repo. It creates `locallift-web` (Docker, Singapore) and `locallift-db` (Postgres). Fill in the secret env vars when asked:
   - `ADMIN_PASSWORD`: a long random password
   - `UPI_VPA`: the UPI ID that receives payments (e.g. `name@okaxis`)
   - `LLM_PROVIDER=anthropic` and `LLM_API_KEY` (optional; without them the human-written copy library is used)
   - leave `RENDER_API_KEY` and `WORKFLOW_SLUG` empty for now (packs then render inside the web service)
2. **Workflow service:** Dashboard → New → Workflow → this repo. Language **Docker**, region **Singapore**, start command `python -m pipeline.workflow`. Name it `locallift-workflows`. Add env var `DATABASE_URL` = the database's **internal** connection string (and `LLM_PROVIDER`/`LLM_API_KEY` if used).
3. **Connect them:** create an API key (Account Settings → API Keys). On `locallift-web` set `RENDER_API_KEY` to it and `WORKFLOW_SLUG=locallift-workflows`. New orders now run on Workflows; check the `pack_started` event's `runner` field or the Workflows dashboard.
4. Open `/admin` and add reps. Test the UPI link with a real phone and a small amount.

## Env vars

`DATABASE_URL`, `ADMIN_PASSWORD`, `ADMIN_USER` (default `admin`), `UPI_VPA`, `UPI_NAME`, `PRICE_STARTER` (199), `PRICE_BUNDLE` (499), `LLM_PROVIDER` (`anthropic` or empty), `LLM_API_KEY`, `LLM_MODEL` (default `claude-opus-5-5`), `RENDER_API_KEY`, `WORKFLOW_SLUG`, `ORDER_LIMIT_PER_HOUR` (8).

## Layout

| Folder | Contents |
|---|---|
| `pipeline/` | rendering, QA, copy, Render Workflows tasks |
| `web/` | FastAPI app, templates, payments, admin |
| `shared/` | `schema.sql` (applied at startup) and the DB helper |
| `ops/` | traction ledger, CRM template |
| `tests/` | render samples and the end-to-end smoke test |
