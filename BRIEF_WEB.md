# Brief: web and payments (Om)

Read `CLAUDE.md` and `ROADMAP.md` first. You own `/web` and `shared/schema.sql`. Your job: the app a shop owner or rep uses, the payment flow, the admin, and deployment. A random team will test the live link at 6:30 PM on Oct 18, so it must work for strangers.

## Status (Oct 18): code done, not deployed. Your remaining tasks, in order

Phases 0-3 below are written and the end-to-end smoke test passes locally. Routes differ slightly from this brief: the order page is `/o/{view_token}` (not `/order/{id}`), the pay page `/pay/{view_token}`, and downloads `/d/{download_token}`. What is left:

1. **Claim the Render credits** (check Discord or the dashboard) before creating paid services. Check whether they cover Workflows compute.
2. **Deploy** with the Blueprint (`render.yaml`; steps in `README.md`). Set `ADMIN_PASSWORD` and `UPI_VPA`. Consider a paid Postgres plan: the free one expires in 30 days with no backups, and orders and the ledger live there. If you upgrade, remove that line from the `SUBMISSION.md` limitations.
3. **Run `python tests/smoke.py <live-url> <admin-password>`** against the live site. It creates an order for "Smoke Test Store" and a rep `SMOKE`: reject or ignore that order and deactivate the rep afterwards so they do not count as traction.
4. **Test UPI on a real phone** with Rs 1-10 (set `PRICE_STARTER` low temporarily, or pay the real amount to yourselves). Try at least two UPI apps. Record the result in `SUBMISSION.md`.
5. **Phone-width check** of every page on a real phone (not done yet).
6. **Own the submission pack** (moved from Aditya): `SUBMISSION.md`, links, final submit by 9:30 PM. See `BRIEF_OPS.md`.
7. After 3:30 PM, only fixes. Help Ayush with shop visits in the afternoon.

## Task order

### Phase 0 (by ~1:00 AM)
- Create `shared/schema.sql` from the contract in `CLAUDE.md` and apply it at startup.
- Deploy a FastAPI hello-world and a Postgres instance on Render. Put all secrets in environment variables.
- Stub `trigger_pack` so you are not blocked by the pipeline: write placeholder images into `pack_items`.

### Phase 1 (1:00-4:30 AM): vertical slice
- `/` landing page: what it is, a "try a sample" button, a "start a pack" button.
- `/create` form: shop name, phone, offer text, languages, festival, optional logo (max 2 MB, image types only), optional rep code (prefilled from `/r/{code}`).
- `/order/{id}` shows a preview. Poll the database until `pack_items` are ready.
- Log `events` rows for each step.

### Phase 2 (9 AM-1 PM): payment and admin
- `/pay/{id}`: shows the plan and amount, a UPI QR and deep link, and an input for the payment reference. Sets status to `awaiting_confirmation`.
- `/admin` (password from env): approve or reject payments, view orders, view and approve the commission ledger, mark payouts. On approval: status `paid`, create a `download_token` with `secrets.token_urlsafe`, create the `ledger` row (commission = amount x rep's percent).
- `/download/{token}`: clean files only for paid orders.
- `/r/{code}`: rep referral link that prefills the code.
- `/admin/funnel`: counts from `events` (visits, orders, payments started, paid, downloads).

### Phase 3 (1:00-3:30 PM)
- `/sample`: demo mode. Creates an order marked `is_sample` for a fake shop with watermarked output and no payment, so a peer can try the product immediately.
- Mobile layout check on a real phone (most shop owners will use one).

## Security and safety basics

- Escape all user text. Validate upload size and type. Basic rate limit on order creation.
- Unguessable download tokens. No secrets in the repo. Admin behind a password.
- Never show another customer's order. Preview pages should use an unguessable id or token, not a plain incrementing number, if time allows.

## Acceptance criteria

- A person on a phone can go from the landing page to a paid, downloadable pack with no help.
- An admin can approve a payment and the rep's ledger updates.
- `/sample` works without payment and without exposing real shop data.
- The funnel page shows real counts from the `events` table.
- `main` deploys from a clean state.

## Notes

- Test the UPI deep link on a real phone with a small amount. Do not assume it works across apps.
- Manual payment confirmation is a limitation. Add it to `SUBMISSION.md`.
- Fallback if the QR is slow to build: show the UPI ID and amount in text and a deep link button.
