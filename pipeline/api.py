"""Interface for the web app: trigger_pack(order_id) -> run id.

With RENDER_API_KEY and WORKFLOW_SLUG set, starts the generate_pack task on Render Workflows.
Otherwise (local dev, or if starting the workflow fails) runs the same steps in a background thread.
"""
import logging
import os
import threading

from shared.db import log_event

from .pack import run_pack_locally

log = logging.getLogger(__name__)


def trigger_pack(order_id: int) -> str:
    slug = os.getenv("WORKFLOW_SLUG")
    if slug and os.getenv("RENDER_API_KEY"):
        try:
            from render import Render

            run = Render().workflows.start_task(f"{slug}/generate_pack", [order_id])
            log_event("pack_started", order_id, meta={"runner": "render_workflows", "run_id": run.id})
            return run.id
        except Exception as exc:
            log.exception("could not start Render workflow, running locally")
            log_event("pack_started", order_id, meta={"runner": "local", "workflow_error": str(exc)[:300]})
    else:
        log_event("pack_started", order_id, meta={"runner": "local"})
    threading.Thread(target=run_pack_locally, args=(order_id,), daemon=True).start()
    return f"local-{order_id}"
