# LocalLift roadmap: phases and distribution

All times are IST. The build started Oct 17 10:00 AM; this plan starts at about 11:30 PM on Oct 17. Targets are goals to calibrate, not predictions.

## Key dates

| When | What |
|---|---|
| Oct 18, 6:30 PM | Peer pairings. Live link and demo must work. Matches are random |
| Oct 18, 8:00-10:00 PM | Peer feedback (test their product, they test ours) |
| Oct 18, 10:00 PM | Submission deadline. Late submissions are not eligible |
| Oct 25, 11:59 PM | Traction evidence (rules say Oct 26; use Oct 25) |
| Oct 31 | Results |
| Nov 6 / Nov 8 / Nov 10 | Dhanteras / Diwali / Bhai Dooj |

## Build phases

**Team change (Oct 18):** Aditya has handed over. Ayush and Om own all remaining work. The code for phases 0-2 is written and passes locally, ahead of plan, but **nothing is deployed yet**, so deployment is now the first job.

| Phase | Time | Goal | Status / exit check | Owner |
|---|---|---|---|---|
| 0 Setup | done | Repo, schema, rendering spike | Done. Devanagari verified (Pillow + RAQM + libfribidi) | |
| 1 Vertical slice | done locally | Form -> templates -> watermarked preview | Done locally. Exit check still open: a stranger opens the **live** link and gets a preview | |
| 2 Core | done locally | Workflows fan-out + QA, UPI paywall, 3 templates, 3 languages, rep ledger | Code done; smoke test passes locally. Workflows not yet run on Render | |
| 2b Deploy | first thing on waking | Claim Render credits. Blueprint (web + Postgres), env vars, Workflow service, connect them | Live URL passes `tests/smoke.py`; one order shows `runner: render_workflows` | Om (web, DB), Ayush (Workflow service) |
| 3 Real use | until 3:30 PM | Real UPI test on a phone, phone-width check, native review of hi/mr copy, 3 real shops served | At least one real payment | Om (UPI, phone check), both (shops) |
| 4 Freeze | 3:30-6:30 PM | **No new features after 3:30 PM.** Demo video, limitations, description, measured Workflows numbers. Live link verified by 6:00 PM | Link works from a fresh phone | Ayush (video, Workflows section), Om (SUBMISSION.md) |
| 5 Submit | 6:30-10:00 PM | Peer feedback, fixes, submit by 9:30 PM | Submitted with 30 minutes spare | Om submits; both online 6:30-10 PM |

**Cut list if behind (cut in this order):** monthly subscription, A4 print layout, rep dashboard UI (keep the ledger table and an admin view), Marathi (keep English + Hindi), extra templates.

## Distribution phases

| Phase | When | Action | Owner |
|---|---|---|---|
| D0 Prep | by noon Oct 18 | Message people who know shop owners or could be reps. Line up 3 shops for the afternoon. Pitch and rep scripts are already in `BRIEF_OPS.md` | Ayush + Om (not started) |
| D1 First sales | Oct 18 afternoon | Generate a pack live in front of the shop owner and close for UPI. Record real orders | Ayush + Om |
| D2 Rep activation | Oct 19-25 | Recruit and onboard reps, daily outreach and demos, run the pricing test | Ayush + Om |
| D3 Festive peak | Oct 26-Nov 10 | Push the festive bundle before Dhanteras; test a monthly offer subscription | Ayush + Om |

## Channels

- **Student reps:** commission on each confirmed sale (30% is a hypothesis). Pay by UPI only after payment is confirmed. Block self-referrals.
- **Direct shop visits and calls:** probably the highest-converting channel (unverified).
- **Personal network:** family and friends who run or know shops.
- **Build in public:** daily posts. There is a separate award that depends on social presence until Oct 31.
- **Happy-shop referrals:** a credit for each neighboring shop a customer brings.

## Metrics and targets (revise after the first 20 conversations)

- Funnel: conversations -> demos -> paid orders -> repeat orders. All counted in the CRM sheet and the `events` table.
- Oct 18: 3 real shops served, at least 1 paid.
- By Oct 25: roughly 30-50 shop conversations and about 10 paid orders (goal only).
- Pricing test: offer about Rs 199 (starter) and about Rs 499 (festive bundle) to different shops. Record which closes and ask each shop what they would pay.
- Evidence to keep: orders export, redacted UPI receipts, the rep ledger, repeat purchases, testimonials with written consent.

## Risks

| Risk | Mitigation |
|---|---|
| Devanagari text renders wrong | Resolved: needs `libfribidi0`, installed by the Dockerfile. Never deploy without the Dockerfile |
| Two people doing three people's work | Distribution is the 40% criterion; do not let deployment polish eat the afternoon shop visits. Cut list still applies |
| Render Workflows is beta (no cron, no checkpointing) | Make every task safe to rerun (idempotent) |
| Manual payment confirmation | State it as a limitation; revisit a payment gateway later |
| Reps cheat or underperform | Commission only on confirmed payment; simple written terms |
| Merge conflicts | Folder ownership, hourly merges |
| Exhaustion | Sleep block; feature freeze at 3:30 PM |
| Legal/tax on commissions and service sales | Not researched; check before scaling |

## Questions to ask in Discord

1. Are paid referral reps acceptable under the rules?
2. Can sales after Oct 25 be added to traction evidence before results on Oct 31?
3. Is there a full scoring breakdown beyond the four criteria?
