# Render Workflow service: setup and test (for Om)

Goal: create `locallift-workflows` on Render, connect the live site to it, prove one real order runs on it, and send Ayush the numbers for the submission. About 30 minutes. Do every Render step **in the Dashboard in a browser**: only the Dashboard offers the **Docker** runtime, and Docker is what makes Hindi/Marathi render correctly (our Dockerfile installs `libfribidi0`). The API, the CLI and Blueprints only offer plain Python.

Never paste a database URL or API key into a file in the repo, a group chat or a public channel.

---

## Step 0. Before you start (2 min)

1. Log into https://dashboard.render.com and switch to the workspace that has `locallift-web` and `locallift-db`.
2. Open **Billing** for that workspace and check that the $50 credits show there. If they are on another account, stop and tell Ayush: the service must live in the same workspace as the database.
3. Have these ready (all in the Dashboard):
   - `locallift-db` → **Connect** → **Internal Database URL** (for the Workflow service)
   - `locallift-db` → **Connect** → **External Database URL** (for the check script on your laptop)

## Step 1. Get the check script without merging (2 min)

`tests/workflow_check.py` is on Ayush's branch `ayush-mypart`, not on `main` yet. Copy just that file (and this guide) into your repo without switching or merging branches:

```
cd <your LocalLift folder>
git fetch origin
git checkout origin/ayush-mypart -- tests/workflow_check.py ops/WORKFLOW_SETUP.md
pip install "psycopg[binary]"
```

This only adds the two files to your working copy; your branch and `main` are unchanged. Do **not** commit them on your branch (they arrive on `main` when Ayush merges). To undo: `git restore --staged tests/workflow_check.py ops/WORKFLOW_SETUP.md` and then delete the two files.

Test that the script can reach the database (read-only, changes nothing):

```
python tests/workflow_check.py "<EXTERNAL_DATABASE_URL>"
```

You should see a table with order 1, runner `local`, about 139 seconds. If you get `SSL connection has been closed unexpectedly`, your IP is not allowed: `locallift-db` → **Info** → **Access Control** → add your current IP, save, and try again.

Write down order 1's `items` number: ______

## Step 2. Create the Workflow service (10 min, mostly waiting for the build)

1. Dashboard → **New** → **Workflow**.
2. Connect the repo `inslot2525-ctrl/LocalLift` (it is public; use the GitHub connection or paste the URL). Branch: **`main`**.
3. Fill in the form exactly:

   | Field | Value |
   |---|---|
   | Name | `locallift-workflows` (exactly; the website uses this name) |
   | Language | **Docker** (not Python 3) |
   | Region | **Singapore** (same as the database, or the internal URL will not work) |
   | Dockerfile Path | leave empty (the Dockerfile is in the repo root) |
   | Start Command | `python -m pipeline.workflow` (required even though the Dockerfile has a CMD) |

4. **Environment variables** (in the form, or on the service's Environment tab right after):
   - `DATABASE_URL` = the **Internal** Database URL
   - If `locallift-web` has `LLM_PROVIDER` and `LLM_API_KEY` set, add the same two here. If not, skip them (the human-written copy is used).
5. Click **Deploy Workflow** and wait for the build to finish (several minutes the first time).

## Step 3. Check the build (2 min)

On the `locallift-workflows` page:

- [ ] Status is live / deployed, no build error.
- [ ] Four tasks are listed: `generate_pack`, `write_copy`, `render_poster`, `bundle_pack`.
- [ ] The logs show the line `pillow raqm: True fribidi: ...`. If it says `raqm: False`, Hindi/Marathi would render broken. Stop and send Ayush the log (the posters would fail with "RAQM/libfribidi missing", by design).

If creating it says **"Payment information is required"** again, the credits do not count as payment info. Take a screenshot, stop, and tell Ayush; we will ask the organisers. Nothing on the website has changed at this point.

## Step 4. Manual test run on an old order (2 min)

1. In `locallift-workflows`, open the `generate_pack` task and start a run (the button to run or trigger the task) with the input:
   ```
   [1]
   ```
2. It should finish quickly and succeed: order 1 is already complete, so every `render_poster` run finds its poster and skips it. This proves the tasks start and can reach the database.
3. Run the check again:
   ```
   python tests/workflow_check.py "<EXTERNAL_DATABASE_URL>"
   ```
   Order 1's `items` must equal the number you wrote down in Step 1, and `dupes` must be `0`.

If the run fails, open it, copy the error from the failing task, and send it to Ayush. Do not continue to Step 5.

## Step 5. Connect the website (3 min)

1. Your account menu → **Account Settings** → **API Keys** → **Create API Key**. Name it `locallift-web`. Copy it now (it is shown once).
2. `locallift-web` → **Environment** → add:
   - `RENDER_API_KEY` = the key
   - `WORKFLOW_SLUG` = `locallift-workflows`
3. Save. If Render does not redeploy on its own, press **Manual Deploy** → **Deploy latest commit**. Wait until it is live.

From now on, every new order on the site starts a workflow run.

## Step 6. One real order through the website (5 min)

1. Open https://locallift-web-jp8m.onrender.com/create (on your phone is fine).
2. Shop name `Workflow Test Shop`, any phone, a short offer such as `20% off all sweets`, languages **English + Hindi**, Diwali. Submit.
3. Watch the progress on the order page. **Important:** the site only falls back to rendering packs itself if the workflow fails to *start*. If the workflow starts but fails on Render, the order page just stops making progress. If you see no previews after about 5 minutes, go to Step 9 (rollback) now.
4. When all previews show, find the order id (Admin → Orders, the newest "Workflow Test Shop") and run:
   ```
   python tests/workflow_check.py "<EXTERNAL_DATABASE_URL>" <ORDER_ID>
   ```
5. Check the order's row:
   - [ ] `runner` = `render_workflows` (if `local`, the line under it shows `workflow_error:`; copy that)
   - [ ] `items` = `28` (18 posters + 10 messages), `dupes` = `0`
   - [ ] `seconds`: note it here: ______
6. The script saved the posters to the `workflow_check_out` folder. Open a file with `_hi_` in its name and compare it with `pipeline/spike_fribidi.png`: the Hindi letters must join the same way, with no broken or floating marks.

## Step 7. Re-run the same order (2 min)

1. In `locallift-workflows`, run `generate_pack` with `[<ORDER_ID>]`.
2. Run the check command from Step 6.4 again. `items` must still be `28` and `dupes` `0`. This shows that re-runs never duplicate items.

## Step 8. Collect the numbers and send them to Ayush (5 min)

From the Workflows dashboard, open the `generate_pack` run for the order from Step 6 and note:

- total task runs: expected 21 (1 `generate_pack` + 1 `write_copy` + 18 `render_poster` + 1 `bundle_pack`): ______
- any runs retried or failed (which task, error): ______
- the slowest `render_poster` run (probably an A4 poster), in seconds: ______
- the credits used so far (Billing), if shown: ______

Send Ayush privately:
1. the output of the check command from Step 6.4 and Step 7
2. one Hindi PNG from `workflow_check_out`
3. the numbers above

Then clean up: **Admin → Orders → Workflow Test Shop → Reject**, so it never counts as a sale.

## Step 9. Rollback (if anything goes wrong)

The website works without Workflows. To go back:

1. `locallift-web` → **Environment** → delete `WORKFLOW_SLUG` (you can leave `RENDER_API_KEY`) → save and redeploy.
2. New orders render inside the web service again (about 139 s on the free plan).
3. An order that got stuck while Workflows was on does not restart itself. Either re-run `generate_pack` with `[<ORDER_ID>]` once the workflow is fixed, or make a new order.
4. Send Ayush the error text or a screenshot so the submission can describe it honestly.

Leaving the `locallift-workflows` service up costs nothing while no task runs (billing is per task run), so there is no need to delete it.

## Quick reference

| Thing | Value |
|---|---|
| Workflow service name / `WORKFLOW_SLUG` | `locallift-workflows` |
| Language / Region | Docker / Singapore |
| Start command | `python -m pipeline.workflow` |
| Env on the workflow | `DATABASE_URL` (internal), optional `LLM_PROVIDER`, `LLM_API_KEY` |
| Env on `locallift-web` | `RENDER_API_KEY`, `WORKFLOW_SLUG` |
| Check script | `python tests/workflow_check.py "<EXTERNAL_DATABASE_URL>" [ORDER_ID]` |
| Live site | https://locallift-web-jp8m.onrender.com |
