# LocalLift: submission draft

Only real figures. The demo video link is the one item still missing.

## Project description

**What it is:** LocalLift gives small local shops done-for-you marketing packs (offer posters, WhatsApp messages and a review request) in their own language, delivered in minutes. Version 1 covers festive offer packs for Diwali.

**Who it is for:** small shop owners (sweet shops, garment and gift stores, general stores) who run festive offers without a designer, and college students who earn a commission as LocalLift reps.

**How it makes money:** (no sales yet at submission; the model below is built and live, but the prices are untested hypotheses)
- Paywall: a free watermarked preview; payment by UPI unlocks clean files in all sizes plus the messages.
- Pricing: Rs 199 starter pack (1 design, 3 sizes, all chosen languages, all messages) and Rs 499 festive bundle (all 3 designs, for Dhanteras to Bhai Dooj). These are starting guesses. Between now and Oct 25 we will offer both to different shops, record which closes, and ask each shop what it would pay.
- Reps earn 30% of each confirmed sale (Rs 59 on a starter pack, Rs 149 on a bundle), paid by UPI only after the customer's payment is confirmed. The commission ledger is built into the admin.
- Strategy: one-time pack and seasonal bundle first; a monthly "weekly offer" subscription to retain shops after the festival (unproven).
- Acquisition: student reps with a commission, direct shop visits, personal network, referrals from happy shops, building in public.

## Failure cases and limitations

Add to this list whenever we find something. Current list:

- Templates are generic; design quality is below a custom designer.
- Hindi and Marathi copy needs native-speaker review; machine copy can sound unnatural.
- Payment confirmation is manual (customer enters a reference; an admin approves). Not suitable at scale.
- Files are stored in the database; this does not scale.
- Demand is seasonal; retention after Bhai Dooj is unproven.
- Existing festival-poster apps and local designers compete on price.
- Commission, tax and GST obligations have not been researched.
- Render Workflows is in beta; no cron or checkpointing, so tasks are written to be safe to rerun.
- Hindi and Marathi only render correctly with the RAQM layout engine, which needs the `libfribidi` system library. Without it, conjuncts break silently (no error), so we run everything from a Dockerfile that installs it. Our QA cannot detect wrong shaping, only missing glyphs.
- The poster QA checks layout facts (margins, overlap, contrast, phone and offer present, glyph coverage). It cannot judge whether a design looks good or whether the copy is right; a human still has to look. (During the build, a line-stacking bug passed every check until we looked at the images; we then added the overlap check.)
- Offer text is limited to 120 characters so it fits on a poster; longer offers fall back to a plain layout or fail QA.
- The offer is printed exactly as typed. If a shop picks Hindi but types the offer in English, the poster mixes languages; we do not translate the offer.
- Payment confirmation is matched by hand against the UTR the customer types. A customer could type someone else's UTR; the admin must check it against the bank statement before approving.
- Self-referrals cannot be detected automatically (reps have no phone field to compare with); the admin reviews commissions before payout.
- The rate limit (orders per IP per hour) lives in memory, so it resets on every deploy and does not work across several instances.
- Preview and order pages use an unguessable token, but anyone who has the link can see the preview and, once paid, the download page. There are no accounts.
- The free Render Postgres plan expires after 30 days (this one on Nov 17, 2026) and has no backups.
- The live web service runs on Render's free plan for now (the paid plan needs a card on the account). Free instances sleep after about 15 minutes idle, so the first visit after a quiet spell takes about a minute to load.
- On the free plan, packs render inside the web service on a small CPU share: the first live smoke-test order (2 languages, 18 posters plus messages) took 139 s from order to all previews, against 6 s on a laptop. A shop owner watching a live demo waits over two minutes.
- Phone-width layout was checked in headless Chromium with mobile emulation at 360 and 390 px (no horizontal scroll on any page, tap targets enlarged to about 44 px), not on a real phone. Admin tables scroll sideways on a phone. The download page for a 3-design, 2-language bundle is long (18 poster rows).
- Tailwind, htmx and fonts load from public CDNs, so a page loaded on a weak connection can show unstyled for a moment.
- Render Workflow services created through the API only offer native runtimes, not our Dockerfile, so `libfribidi0` (needed for correct Hindi/Marathi shaping) is missing there. A build step (`pipeline/vendor_fribidi.py`) downloads and hash-checks Debian's package; this works in a bare Python container but has not yet run on Render.
- Render Workflows has not run on Render: creating the Workflow service returned `HTTP 402: Payment information is required` (Workflows bill per task-run and our workspace has no card). Claiming Render's $50 hackathon credits did not remove this: the Dashboard still asks to add a card before it creates a Workflow service. Every live pack renders inside the web service on the free CPU (see the 139 s figure above).
- No traction yet: at submission time no real shop has ordered or paid. Everything on the live database so far is our own testing.

## How we used Render Workflows

**Status: designed and tested locally, not run on Render, and not used by the live site.** Creating the Workflow service needs a card on the Render account (`HTTP 402: Payment information is required`, even after claiming the hackathon credits), and our team has no card, so on Oct 18 we decided to skip it for the hackathon. Live packs render inside the web service through the fallback described below. We are describing the design, not claiming a running deployment.

Design (`pipeline/workflow.py`, details in `pipeline/README.md`):
- `generate_pack(order_id)` is the parent task. It runs `write_copy` (LLM copy with a human-written fallback), then fans out one `render_poster` task per language x size x design (18 for a 2-language order) in parallel, then `bundle_pack` audits the pack and records `preview_ready`.
- Each `render_poster` run renders, runs our automatic QA (margins, overlap, contrast, phone and offer present, glyph coverage), retries once with a simpler layout if QA fails, and stores the poster plus a watermarked preview.
- Per-task timeouts and retries with exponential backoff. Every task is idempotent (writes keyed on order, kind, language, size, design), so Render's retries and manual re-runs never duplicate items.
- If Workflows cannot be started, the web app runs the same steps in a thread pool and logs which path ran (`runner: render_workflows` or `local`).
- What we learned: Workflow services created through Render's API only offer native runtimes, so the Devanagari shaping library our Dockerfile installs is missing there; a hash-checked build step (`pipeline/vendor_fribidi.py`) supplies it.

## Traction (due Oct 25, 11:59 PM IST)

Only real, exported data. Redact personal payment details. Exclude test data: on the live database, order 1 ("Smoke Test Store", rep `SMOKE`, deactivated) is our own smoke test, not a sale.

| Date | Shop (if consented) | Rep | Plan | Amount (Rs) | Outcome | Evidence |
|---|---|---|---|---|---|---|
| (none yet) | | | | | | |

Funnel summary as of Oct 18 submission: no shop conversations, demos or paid orders recorded yet (`ops/traction_ledger.md` is empty apart from our test order). This section will be filled with real, exported data by Oct 25.

## Links

- Live URL: https://locallift-web-jp8m.onrender.com (try `/sample` for a demo pack with no payment)
- Repo: https://github.com/inslot2525-ctrl/LocalLift
- Demo video: **ADD THE LINK BEFORE SUBMITTING**
