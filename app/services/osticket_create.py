"""Create a ticket in a local osTicket install via scripts/osticket/create_ticket.php (needs php and the install's files)."""
import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "osticket" / "create_ticket.php"


class TicketCreateError(RuntimeError):
    pass


def create_ticket(name: str, email: str, subject: str, message: str, topic: str | None) -> str:
    root = os.path.expanduser(os.environ.get("OSTICKET_DIR", "~/osticket"))
    if not Path(root, "bootstrap.php").is_file():
        raise TicketCreateError("osTicket install not found. Set OSTICKET_DIR to its folder.")
    payload = json.dumps({"name": name, "email": email, "subject": subject, "message": message, "topic": topic or ""})
    try:
        proc = subprocess.run(["php", str(SCRIPT), root], input=payload, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TicketCreateError(f"Could not run php: {exc}") from exc
    try:
        res = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        raise TicketCreateError("osTicket did not return a result") from None
    if not res.get("ok"):
        raise TicketCreateError(f"osTicket refused the ticket: {res.get('error')}")
    return res["number"]
