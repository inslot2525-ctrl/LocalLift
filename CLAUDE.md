# LocalLift: project brief for Claude Code

Read this file first in every session. Then read `ROADMAP.md` and your own brief (`BRIEF_PIPELINE.md`, `BRIEF_WEB.md` or `BRIEF_OPS.md`). If you are not sure which brief is yours, ask the human.

## Status and handover (updated Oct 18, early morning IST)

**Aditya has handed over and is not working on the project for now. Ayush and Om own everything from here.** Do not assign tasks to Aditya or wait on him.

**Built and pushed to `main`** (one session built both folders, so the per-folder split below describes ownership from now on, not who wrote what):
- `pipeline/`: Pillow + RAQM renderer (Hindi/Marathi verified by eye), 3 templates x 3 sizes, automatic QA with a simple-layout retry, watermarked previews, LLM copy with a human-written fallback library (en/hi/mr), Render Workflows tasks (`workflow.py`), `trigger_pack` (`api.py`) with a local thread-pool fallback.
- `web/`: every route in `BRIEF_WEB.md` (form, previews with live progress, UPI pay page, admin approve/reject, rep ledger, downloads + ZIP, `/r/{code}`, `/sample`, `/admin/funnel`), rate limit, upload checks, unguessable order and download tokens.
- `Dockerfile` (installs `libfribidi0`, required for Devanagari), `docker-compose.yml`, `render.yaml`, `tests/smoke.py` (22-step end-to-end test: **passes locally**), `tests/render_samples.py` (27 posters: all pass QA).
- `pipeline/README.md` has the rendering findings and the Workflows write-up for the submission. `README.md` has the deploy steps.

**Not done or not verified yet** (the critical path to 6:30 PM; owners in the briefs):
1. **Deployed (Oct 18, 10:40 AM):** https://locallift-web-jp8m.onrender.com, web service `locallift-web` + Postgres `locallift-db` (both **free** plan, Singapore, Om's Render workspace, created via the API, auto-deploys from `main`). `tests/smoke.py` passes against it (pack in 139 s on the free CPU). Still open: add a card or claim credits and switch the web service to `starter`; create the Workflow service (Dashboard only, needs Ayush + Om) and set `RENDER_API_KEY` / `WORKFLOW_SLUG` on the web service. Admin password: ask Om (not in the repo).
2. Render Workflows has never run on Render. Until it has, the submission must not claim it; the app falls back to rendering inside the web service.
3. The UPI deep link and QR are untested on a real phone.
4. Phone width checked in headless Chromium (360/390 px, mobile emulation) and fixed; not yet on a real phone.
5. Hindi and Marathi copy has had no native-speaker review.
6. Schema additions below need Ayush and Om to agree (Aditya is away, so two of three is the quorum for now).
7. No real shops, no traction yet. Distribution work moved to Ayush and Om (`BRIEF_OPS.md`).

**Schema additions beyond the contract** (in `shared/schema.sql`, pending agreement):
- `orders.view_token text unique`: order and preview pages use it instead of the numeric id.
- `create unique index ledger_order_uniq on ledger(order_id)`: approving twice cannot pay a commission twice.
- Message rows use `template_id` as the slot: `wa1`, `wa2`, `wa3`, `review`, `headline`. The contract's empty string would let the unique key hold only one message per language. The `headline` row stores the poster headline so re-runs reuse it.

## What we are building

LocalLift gives small local shops done-for-you marketing packs (offer posters, WhatsApp messages, review requests) in their own language, delivered in minutes. Student reps sell and set up packs in person and earn a commission on every confirmed sale. Version 1 covers **festive offer packs** only (Diwali first). Do not build general marketing features.

Flow:
1. A shop owner (or a rep on their behalf) fills a 60-second form: shop name, phone, optional logo, offer text, language(s), festival.
2. The pipeline generates a pack: status-size (1080x1920), square (1080x1080) and print (A4, 2480x3508) posters, three WhatsApp broadcast messages, one review-request message.
3. A watermarked preview is free. Paying by UPI unlocks clean files.
4. Each rep has a referral code and a commission ledger.

## Hackathon context (RevHack 2026, run by EYFI / Polygnan)

- Judges ask one question: "Could this earn?" Weights: earning potential and plan (40%, traction signals help), product working and UI/UX (20%), innovation and impact (10%), understanding and presentation including failure cases and limitations (30%). The full breakdown was said to be shared before kickoff; check Discord.
- It must be a real earning vehicle, not a tech demo.
- Deadlines (IST): peer pairings Oct 18 6:30 PM (live link + demo must work); peer feedback Oct 18 8-10 PM; **submission Oct 18 10:00 PM**; traction evidence **Oct 25 11:59 PM** (dashboard says Oct 25, rules page says Oct 26: use Oct 25); results Oct 31.
- Submission needs: public GitHub repo, demo video up to 5 minutes (shows it working and how it earns), project description (what, who for, how it makes money), failure cases and limitations, how we used Render Workflows.
- Using Render Workflows is optional but required for the separate Render award ($500/$300/$100 credits for the top 3), judged on how well and creatively it is used.

## Non-negotiables

1. **Honesty.** Never invent traction numbers, customers, testimonials, receipts or screenshots. Anything shown in a demo that is not real must be labeled "sample". Only real figures go in the submission.
2. **Limitations are a deliverable (30% of the score).** Whenever you discover something that does not work or is risky, add it to the "Failure cases and limitations" section of `SUBMISSION.md`.
3. **Privacy.** Collect the minimum: shop name, phone, offer text, optional logo. No secrets in the repo. Use environment variables.
4. **Scope.** We have about 19 hours until the live link must work. Do not add features that are not in `ROADMAP.md` without asking the human. Follow the cut list there if time runs short.
5. **Real earning path.** Every decision should help a real shop pay for a real pack.

## Stack (defaults; change only with all three humans agreeing)

- Python 3.11+, FastAPI, Jinja2 templates + HTMX, Tailwind via CDN. No JS build step.
- Postgres on Render. Plain SQL in `shared/schema.sql` applied at startup. No Alembic.
- Render web service + **Render Workflows (Python SDK)** for pack generation. The Workflows launch post says Python tasks use an `@app.task` decorator, tasks can call other tasks, each task can set retries and a timeout, and the product is in beta (cron triggers, checkpointing and vertical autoscaling are listed as planned, so do not rely on them). Read Render's current docs before coding.
- Files (preview and final images) are stored as `bytea` in Postgres for v1. This is fine at hackathon scale and avoids object-storage credentials. It does not scale; note it as a limitation.
- Payments v1: UPI deep link + QR, manual confirmation. The customer enters a payment reference; an admin approves it. Razorpay or similar is a later step.
- LLM for copy: provider chosen by env `LLM_PROVIDER`, key in `LLM_API_KEY`. **Every LLM call needs a deterministic fallback** (a human-written copy library per festival and language).
- Fonts: an open-licensed Devanagari font (for example Noto Sans Devanagari; verify the license before shipping).

## Repo layout and ownership

```
/pipeline   Ayush        rendering, copy, Render Workflows tasks
/web        Om           FastAPI app, UI, payments, admin, deploy
/ops        Ayush + Om   outreach docs, scripts, CRM, traction ledger, demo assets (was Aditya's; see BRIEF_OPS.md)
/shared                  schema.sql and the DB helper (change only with Ayush and Om agreeing while Aditya is away)
/tests                   smoke test and render samples (anyone may edit; keep them passing)
CLAUDE.md  ROADMAP.md  BRIEF_*.md  SUBMISSION.md
```

Edit only your own folder. If you need a change elsewhere, tell the human to ask the owner. `SUBMISSION.md` is owned by Om (see `BRIEF_OPS.md`); anyone may add to its limitations list.

## Data contract (schema.sql)

```sql
create table reps (
  code text primary key, name text not null, upi_id text,
  commission_pct int not null default 30, active boolean default true,
  created_at timestamptz default now());

create table shops (
  id serial primary key, name text not null, phone text, city text,
  created_at timestamptz default now());

create table orders (
  id serial primary key,
  shop_id int references shops(id),
  rep_code text references reps(code),
  festival text not null,               -- 'diwali' for v1
  languages text[] not null,            -- e.g. {'en','hi','mr'}
  offer_text text not null,
  logo bytea, logo_mime text,
  plan text not null,                   -- 'starter' | 'festive_bundle'
  amount_inr int not null,
  status text not null default 'preview',  -- preview | awaiting_confirmation | paid | rejected
  payment_ref text,
  download_token text unique,
  is_sample boolean not null default false,
  created_at timestamptz default now(), paid_at timestamptz);

create table pack_items (
  id serial primary key,
  order_id int references orders(id),
  kind text not null,                   -- poster | message
  language text not null,
  size text not null default '',        -- status | square | a4 | '' for messages
  template_id text not null default '', -- '' for messages (empty string, not null, so the unique key works)
  body text,                            -- message text for kind = message
  mime text, file_bytes bytea, preview_bytes bytea,
  qa_status text not null default 'pending',  -- pending | passed | failed
  qa_notes text,
  created_at timestamptz default now(),
  unique (order_id, kind, language, size, template_id));

create table ledger (
  id serial primary key, order_id int references orders(id),
  rep_code text references reps(code), amount_inr int not null,
  status text not null default 'pending',  -- pending | approved | paid_out
  created_at timestamptz default now());

create table events (
  id bigserial primary key, ts timestamptz default now(),
  kind text not null,                   -- visit | form_start | order_created | preview_ready | payment_started | paid | download
  order_id int, rep_code text, meta jsonb);
```

Interface between web and pipeline:
- `/pipeline/api.py: trigger_pack(order_id: int) -> str` starts the Render Workflow and returns a run id.
- The pipeline writes `pack_items` rows and sets their `qa_status`. The web app polls the database; it never calls pipeline internals.
- If `RENDER_API_KEY` or `WORKFLOW_SLUG` is unset, or the workflow fails to start, `trigger_pack` runs the same steps in a background thread in the web service and returns `local-<id>`. The `pack_started` event's `meta.runner` records which path ran (`render_workflows` or `local`).

## Working agreements for Claude Code sessions

- Branches: `ayush/pipeline`, `om/web` (create them from `main`; `aditya/ops` is stale, do not use it). Merge to `main` at least hourly. **`main` must always deploy.**
- Run the app and your tests locally before merging: `docker compose up --build`, then `python tests/smoke.py http://localhost:8000 localadmin`. Never push a broken `main`. Run renders through Docker: Pillow on Windows has no RAQM and draws Hindi/Marathi wrong.
- Small commits with a folder prefix, for example `pipeline: add quality check`.
- Tell the human before adding a dependency. Prefer pip-installable packages with no system libraries, unless we add a Dockerfile.
- Log analytics events (see the `events` table) for every step of the funnel.
- Time-box every task using the budgets in your brief. If you exceed a budget, stop, summarize the blocker and propose the fallback.
- Checkpoints where Ayush and Om integrate and test together: 1:00 PM, 3:30 PM (IST). Feature freeze at 3:30 PM on Oct 18.

## Unverified assumptions (check, do not assume)

- Render Workflows on Render itself: the code follows Render's Python SDK docs (`render>=1.0.1`, `Workflows`, `@app.task`, `ctx.run`, `Render().workflows.start_task("<slug>/<task>", [args])`) but has never run there. Docker-based Workflow services can only be created in the Dashboard.
- Settled: Devanagari shaping works with Pillow + RAQM when `libfribidi0` is installed (see `pipeline/README.md`).
- UPI deep-link format works in common UPI apps. The common format is `upi://pay?pa=<vpa>&pn=<name>&am=<amount>&cu=INR&tn=<note>`; test it on a real phone.
- Legal and tax treatment of commissions, GST on sales, and data-protection obligations. We have not researched these.
- Whether reps count under the hackathon rules (teams are up to 3 members; reps are not team members).
