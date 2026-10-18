# Pipeline: how a pack is made

## Rendering (spike result, Oct 17)

- **Chosen: Pillow + RAQM** (option A in the brief). Verified by looking at the output: Hindi `दीपावली की हार्दिक शुभकामनाएँ` and Marathi `दिवाळीच्या हार्दिक शुभेच्छा` render with correct conjuncts and matras (`spike_fribidi.png`).
- **It needs one system library, `libfribidi0`.** Pillow's wheels bundle RAQM and HarfBuzz but load FriBiDi from the system. Without it (Windows, or a bare `python:3.12-slim` container), `features.check("raqm")` is False and Devanagari renders broken: the reph in हार्दिक and the conjunct in शुभेच्छा come apart. So both the web service and the Workflow service run from our `Dockerfile`, which installs it.
- Fonts: Noto Sans Devanagari and Noto Sans (SIL Open Font License 1.1, `fonts/OFL.txt`). The Devanagari font has no Latin letters, so text is split into script runs and each run is drawn with the right font.

## Pack contents per order

For each chosen language: 3 designs (diya, rangoli, lantern) x 3 sizes (status 1080x1920, square 1080x1080, A4 2480x3508) = 9 posters, plus 3 WhatsApp messages, 1 review request and the poster headline. Two languages = 18 posters + 10 text items. The preview shows everything watermarked; the plan decides what the download unlocks (starter: diya only; bundle: all three).

## How we use Render Workflows

`pipeline/workflow.py` is a Render Workflows service (start command `python -m pipeline.workflow`). In the Dashboard it can use the Docker runtime (same image as the web app); Render's API only offers native runtimes for Workflow services, so for a Python-runtime service the build command is `pip install -r requirements.txt && python -m pipeline.vendor_fribidi` and the start command is prefixed with `LD_LIBRARY_PATH=/opt/render/project/src/.vendor/lib`. `vendor_fribidi.py` downloads Debian's `libfribidi0` package, checks its SHA-256 against Debian's index and unpacks the library (checked in a bare `python:3.12-slim` container: RAQM becomes available and every Hindi/Marathi sample passes QA with correct conjuncts). `render_poster` refuses Hindi/Marathi if RAQM is still missing, so a bad instance fails loudly. The web app calls `trigger_pack(order_id)` (`pipeline/api.py`), which starts the `generate_pack` task through the Render Python SDK (`Render().workflows.start_task("<slug>/generate_pack", [order_id])`).

```
generate_pack(order_id)                        parent task, timeout 15 min, 1 retry
 ├─ write_copy(order_id)                       LLM copy -> validated -> stored; falls back to the human-written library
 ├─ render_poster(order, lang, size, design)   one task per poster, all started at once with asyncio.gather,
 │    x 9 per language                         each on its own instance; renders, runs QA, retries once with a
 │                                             simpler layout if QA fails, stores PNG + watermarked preview
 └─ bundle_pack(order_id)                      pack-level audit: counts passed/failed items, records preview_ready
```

- **Fan-out:** a 2-language order starts 18 `render_poster` runs in parallel. A4 posters are the slow ones; running them in parallel should keep preview time close to one A4 render plus instance start-up. [TODO: measure on Render and replace with real numbers. Locally, the thread-pool fallback made a 2-language pack in about 9 s.]
- **Retries and timeouts per task:** default 2 retries with exponential backoff (2 s, x2), `render_poster` 180 s, `write_copy` 120 s, `bundle_pack` 60 s.
- **Idempotency:** Workflows is in beta (no checkpointing), so every task checks the database first and writes with `on conflict do nothing` on the unique key (order, kind, language, size, template). Retrying a task, or re-running the whole workflow for an order, never duplicates items. `write_copy` stores the headline so a re-run reuses the same copy rather than calling the LLM again.
- **Quality gate inside each render task** (`qa.py`): text inside a safe margin, no overlapping lines, WCAG contrast (4.5:1, or 3:1 for large text), the phone number and full offer text present on the poster, and every character covered by the font (no missing-glyph boxes). Failures are recorded in `pack_items.qa_status`/`qa_notes` and shown in the admin order view.
- **Status (Oct 18):** not yet run on Render. Creating the Workflow service through Render's API returned `HTTP 402: Payment information is required`: Workflows bill per task-run on the `flex` plan and the workspace has no card yet. Until a card or credits are added, every live pack renders through the fallback below.
- **Fallback:** if `RENDER_API_KEY`/`WORKFLOW_SLUG` are not set, or the workflow cannot be started, `trigger_pack` runs the same steps in a thread pool inside the web service and records `runner: local` on the `pack_started` event, so we can always tell which path produced a pack.

## Measuring a run

Time from `pack_started` to `preview_ready` per order, and which runner made it:

```sql
select s.order_id, s.meta->>'runner' as runner, extract(epoch from r.ts - s.ts)::int as seconds,
       r.meta->>'passed' as passed, r.meta->>'failed' as failed
from events s join events r on r.order_id = s.order_id and r.kind = 'preview_ready'
where s.kind = 'pack_started' order by s.order_id desc;
```

Retries and per-task durations are in the Workflows dashboard (each `render_poster` run is listed under its `generate_pack` parent). On a Hobby workspace Render starts at most 16 CPU of new compute per minute, so a 2-language order (18 posters on `flex`, up to 1 CPU each) may queue a few runs.

## Showing QA in the demo

Checked locally (English, all 3 designs x 3 sizes). The web form allows up to 50 characters of shop name and 120 of offer:

- **Retry with the simple layout:** shop `Shree Ganesh Mahalaxmi Sweets and Namkeen Bhandar`, offer `Flat 25% off on all dry fruit gift boxes, kaju katli, soan papdi and every sweet box above Rs 999 till Bhai Dooj!!`. 7 posters pass first time; the rangoli and lantern square posters do not fit, are redrawn with the simple layout and pass, with the note `first layout failed (text did not fit at minimum size); used simple layout`.
- **Hard failure:** a shop name that is one long word, e.g. `Supercalifragilisticexpialidociousmegasweetsshop`. Words are never broken, so the name runs past the edge and every poster is marked `failed` (`text did not fit at minimum size; shop outside safe margin`), even after the retry.

Both show in `/admin/orders/{id}` with their notes; the download page marks failed posters "check before posting".

## Running locally

```
docker build -t locallift .
docker run --rm -v "$PWD/out:/out" locallift python -m tests.render_samples /out   # all designs, sizes, languages + QA
docker compose up --build                                                          # full app on :8000
python tests/smoke.py http://localhost:8000 localadmin                             # end-to-end check
```
