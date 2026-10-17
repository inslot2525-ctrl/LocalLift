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
- The free Render Postgres plan expires after 30 days and has no backups.
- [TODO: add anything found during the build]

## How we used Render Workflows

[TODO: Ayush to paste from `/pipeline/README.md`. Describe the parent task, the fan-out per language x size x template, the quality-check task, the bundle task, retries and idempotency, and what we learned.]

## Traction (due Oct 25, 11:59 PM IST)

Only real, exported data. Redact personal payment details.

| Date | Shop (if consented) | Rep | Plan | Amount (Rs) | Outcome | Evidence |
|---|---|---|---|---|---|---|
| [TODO] | | | | | | |

Funnel summary: conversations [TODO], demos [TODO], paid orders [TODO], repeat orders [TODO].

## Links

- Live URL: [TODO]
- Repo: [TODO]
- Demo video: [TODO]
