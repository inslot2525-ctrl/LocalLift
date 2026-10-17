"""Render Workflows service. Start command on Render: python -m pipeline.workflow

generate_pack(order_id)
  -> write_copy(order_id)                         LLM copy with library fallback, stores messages
  -> render_poster(...) x (language x template x size), all in parallel, each on its own instance
  -> bundle_pack(order_id)                        pack-level audit, records preview_ready
Every task is idempotent (see pack.py), so Render's retries and manual re-runs never duplicate items.
"""
import asyncio

from render import Retry, TaskContext, Workflows

from . import pack

app = Workflows(
    default_retry=Retry(max_retries=2, wait_duration_ms=2000, backoff_scaling=2),
    default_timeout=300,
)


@app.task(timeout_seconds=120)
def write_copy(ctx: TaskContext, order_id: int) -> dict:
    return pack.write_copy(order_id)


@app.task(timeout_seconds=180)
def render_poster(ctx: TaskContext, order_id: int, language: str, size: str, template_id: str,
                  headline: str, cta: str) -> dict:
    return pack.render_one(order_id, language, size, template_id, headline, cta)


@app.task(timeout_seconds=60)
def bundle_pack(ctx: TaskContext, order_id: int) -> dict:
    return pack.bundle_pack(order_id)


@app.task(timeout_seconds=900, retry=Retry(max_retries=1, wait_duration_ms=5000, backoff_scaling=1.5))
async def generate_pack(ctx: TaskContext, order_id: int) -> dict:
    order = pack.load_order(order_id)
    copy = await ctx.run(write_copy, order_id)
    results = await asyncio.gather(
        *[
            ctx.run(render_poster, order_id, lang, size, t, copy[lang]["headline"], copy[lang]["cta"])
            for lang, size, t in pack.item_specs(order)
        ],
        return_exceptions=True,
    )
    failed_runs = sum(isinstance(r, BaseException) for r in results)
    summary = await ctx.run(bundle_pack, order_id)
    return {**summary, "failed_runs": failed_runs}


if __name__ == "__main__":
    app.start()
