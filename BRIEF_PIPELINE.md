# Brief: pipeline (Ayush)

Read `CLAUDE.md` and `ROADMAP.md` first. You own `/pipeline`. Your job: turn an order into a pack of posters and messages, using Render Workflows in a way that is real and creative (a separate award depends on it).

## Task order and time budgets

### 1. Rendering spike (45 min max, do this first)

Goal: render these strings correctly with conjuncts and matras, with no missing-glyph boxes:
- Hindi: `दीपावली की हार्दिक शुभकामनाएँ`
- Marathi: `दिवाळीच्या हार्दिक शुभेच्छा`

Test options in this order and stop at the first that works (look at the output image yourself):
- A. Pillow with the RAQM layout engine (check that it is actually enabled).
- B. HTML/CSS rendered to an image with a headless browser.
- C. HTML -> PDF (WeasyPrint) -> PNG.
- D. Any SVG renderer that shapes complex scripts.

**Then run the same render inside a deployed Render Workflows task**, not just locally. Many system libraries available on a laptop are missing in a task container. If the chosen method needs system packages, tell the human so we can add a Dockerfile. Write the result in `/pipeline/README.md`.

### 2. First template (Phase 1)

`render_item(spec: dict) -> bytes` returns PNG bytes. Start with one template, 1080x1080, English and Hindi. `spec` contains shop name, phone, offer text, language, size, template id, optional logo bytes.

### 3. Copy generation

`generate_copy(order) -> dict` returns poster headlines and three WhatsApp messages plus a review-request message for each language. Use an LLM with a short prompt, and **always fall back to a human-written copy library** (`/pipeline/copy_library/`) per festival and language when the LLM fails or returns something invalid. Ask Aditya to get native-speaker review of Hindi and Marathi copy.

### 4. Workflows (Phase 2)

- Parent task `generate_pack(order_id)` reads the order, then fans out `render_item` tasks across language x size x template.
- `quality_check` task, then `bundle_pack` to write `pack_items` rows and set `qa_status`.
- Each task must be **idempotent**: skip work already recorded for the same (order, kind, language, size, template). Set per-task retries and timeouts. Do not rely on cron or checkpointing (not available yet).
- Expose `trigger_pack(order_id) -> run_id` in `/pipeline/api.py` for the web app.

### 5. Quality checks (verifiable, automatic)

- Text stays inside a safe margin; no overflow.
- Contrast between text and background above a stated threshold.
- Phone number and offer text are present in the image.
- No missing-glyph boxes (check glyph coverage in the font).
If a check fails, regenerate once with a simpler layout; otherwise mark `failed` with notes.

### 6. Sizes, previews and templates

- Sizes: status 1080x1920, square 1080x1080, A4 print 2480x3508.
- Preview images are low resolution with a diagonal "PREVIEW - LocalLift" watermark. Clean files are only served after payment.
- Three templates. Design them yourself from simple shapes (no copyrighted art, no scraped images). Use open-licensed fonts and verify licenses.

## Acceptance criteria

- A stranger can create an order and see correct Hindi and English previews.
- The pack workflow completes with a mix of passed and failed QA items, failures visible in the database.
- Re-running the workflow does not duplicate items.
- `/pipeline/README.md` explains how Render Workflows is used, in a form we can paste into the submission.

## Fallback if you are stuck

If Workflows cannot run the renderer in time, keep the fan-out in a web-side task queue and tell the human immediately, so we describe it honestly in the submission and do not claim the Render award use.
