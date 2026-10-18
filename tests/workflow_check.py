"""Read-only check of pack runs in a database (use the live DB's EXTERNAL connection string).

Usage: python tests/workflow_check.py DATABASE_URL [ORDER_ID] [OUT_DIR]
Prints, per recent order: runner (render_workflows | local), seconds from pack_started to preview_ready,
item counts by QA status and any duplicate items. With ORDER_ID it also saves that order's posters
(full-size PNGs) to OUT_DIR (default: workflow_check_out) so Hindi/Marathi can be checked by eye.
"""
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

url = sys.argv[1]
order_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
out = Path(sys.argv[3] if len(sys.argv) > 3 else "workflow_check_out")

with psycopg.connect(url, row_factory=dict_row) as conn:
    runs = conn.execute(
        """select s.order_id, s.ts, s.meta->>'runner' as runner, s.meta->>'run_id' as run_id,
                  s.meta->>'workflow_error' as error,
                  (select extract(epoch from min(r.ts) - s.ts)::int from events r
                    where r.order_id = s.order_id and r.kind = 'preview_ready') as seconds
           from events s where s.kind = 'pack_started' order by s.ts desc limit 15"""
    ).fetchall()
    print(f"{'order':>5}  {'runner':17} {'seconds':>7}  items  passed failed  dupes  started")
    for r in runs:
        counts = conn.execute(
            "select qa_status, count(*) as n from pack_items where order_id = %s group by qa_status", (r["order_id"],)
        ).fetchall()
        c = {x["qa_status"]: x["n"] for x in counts}
        dupes = conn.execute(
            """select count(*) as n from (select 1 from pack_items where order_id = %s
               group by kind, language, size, template_id having count(*) > 1) d""", (r["order_id"],)
        ).fetchone()["n"]
        print(f"{r['order_id']:>5}  {r['runner'] or '?':17} {r['seconds'] if r['seconds'] is not None else '-':>7}  "
              f"{sum(c.values()):>5}  {c.get('passed', 0):>6} {c.get('failed', 0):>6}  {dupes:>5}  {r['ts']:%H:%M:%S}")
        if r["error"]:
            print(f"       workflow_error: {r['error']}")
    if order_id:
        out.mkdir(exist_ok=True)
        rows = conn.execute(
            """select language, size, template_id, qa_status, qa_notes, file_bytes from pack_items
               where order_id = %s and kind = 'poster' order by language, template_id, size""", (order_id,)
        ).fetchall()
        for p in rows:
            name = f"{order_id}_{p['language']}_{p['template_id']}_{p['size']}.png"
            (out / name).write_bytes(bytes(p["file_bytes"]))
            print(f"saved {name:32} {p['qa_status']:7} {p['qa_notes'] or ''}")
        print(f"{len(rows)} posters in {out.resolve()}")
