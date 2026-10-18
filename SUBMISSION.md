# LocalLift: submission draft

Fill this in as we go. Only real figures. Anything marked [TODO] must be completed or removed before submitting.

## Project description

**What it is:** LocalLift gives small local shops done-for-you marketing packs (offer posters, WhatsApp messages and a review request) in their own language, delivered in minutes. Version 1 covers festive offer packs for Diwali.

**Who it is for:** small shop owners (sweet shops, garment and gift stores, general stores) who run festive offers without a designer, and college students who earn a commission as LocalLift reps.

**How it makes money:** [TODO: confirm after the first sales]
- Paywall: a free watermarked preview; payment unlocks clean files in all sizes plus the messages.
- Pricing (hypotheses, testing now): about Rs 199 starter pack, about Rs 499 festive bundle (Dhanteras to Bhai Dooj). Final prices and the reasons: [TODO from the pricing test].
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
- Render Workflows can build from our Dockerfile (Language "Docker", which installs `libfribidi0` for Hindi/Marathi shaping), but Docker-based workflows can only be created in the Dashboard; through the API, CLI or a Blueprint only native runtimes are offered, where `libfribidi0` is missing. For a native Python service, a build step (`pipeline/vendor_fribidi.py`) downloads and hash-checks Debian's package; this works in a bare Python container but has not yet run on Render. Docker workflows also cannot run locally with the Render CLI's task server.
- Render Workflows has not run on Render yet: creating the Workflow service returned `HTTP 402: Payment information is required` (Workflows bill per task-run and our workspace has no card). Until it does, every live pack renders inside the web service on the free CPU (see the 139 s figure above).
- Words are never broken across lines. A shop name or offer with one very long word (for example a 48-letter name with no spaces) runs past the poster edge; QA marks every poster `failed` even after the simple-layout retry, and the shop has to shorten the name.
- [TODO: add anything found during the build]

## How we used Render Workflows

**Status: written and tested locally, not yet run on Render.** Creating the Workflow service returned `HTTP 402: Payment information is required`; live packs currently render inside the web service. [TODO: replace with real run numbers if a card or credits get the service running before submission.]

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
| [TODO] | | | | | | |

Funnel summary: conversations [TODO], demos [TODO], paid orders [TODO], repeat orders [TODO].

## Links

- Live URL: https://locallift-web-jp8m.onrender.com (try `/sample` for a demo pack with no payment)
- Repo: https://github.com/inslot2525-ctrl/LocalLift
- Demo video: [TODO]
