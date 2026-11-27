"""Reset the L1/L2/L3 demo for a ticket so it can be shown again. Optionally apply the workflow migration first.

  python scripts/reset_demo.py 946493 --migrate     # first time: creates fix_runs / fix_audit_log, then clears the ticket
  python scripts/reset_demo.py 946493               # between demo runs
Writes to the Postgres named in .env (PG_*). Use --dry-run to see what would happen.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)
from app.routers.tickets import get_conn  # noqa: E402

MIGRATION = ROOT / "db" / "migrations" / "2026-11-24_fix_workflow.sql"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket_id")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(f"host={os.environ.get('PG_HOST')} ticket={a.ticket_id} migrate={a.migrate} dry_run={a.dry_run}")
    if a.dry_run:
        return
    with get_conn() as c:
        if a.migrate:
            c.execute(MIGRATION.read_text())
        n1 = c.execute("DELETE FROM fix_runs WHERE ticket_id=%s", (a.ticket_id,)).rowcount
        n2 = c.execute("DELETE FROM fix_audit_log WHERE ticket_id=%s", (a.ticket_id,)).rowcount
    print(f"cleared {n1} run(s) and {n2} audit row(s)")


if __name__ == "__main__":
    main()
