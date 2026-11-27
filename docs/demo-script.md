# Demo script: from user question to approved data fix (about 6 minutes)

Setup once: `python scripts/reset_demo.py 946493 --migrate`, `cd ui && npm run build`, `uvicorn app.main:app --port 7000`, sync the seeded tickets (`POST /api/osticket/sync`).
Between runs: `python scripts/reset_demo.py 946493`.
Local-only run with no database writes: start the server with `FIX_STORE=memory`.

1. **L0, Self-service chat.** Type "Our GL final audit shows a credit but payroll went up". Show the safe next steps and "Still stuck? Raise a ticket". Only the card's reviewed self-service text is shown; internal diagnosis never is.
2. **Ticket #946493 (AI Insights).** Open it. Workbench shows "Not started".
3. **L1.** Run L1. Green = already in the ticket, amber = still missing, plus the message to the requester.
4. **L2.** Continue to L2. Each read-only check, what was found, and the conclusion (exposure basis 369,412 vs audit form 440,000). The data is labelled sample data, not a live PolicyCenter.
5. **L3.** Escalate to L3. Show the Gosu script, the six safety checks, the expected effect, and the change requirement (download Markdown / JSON for the downstream project).
6. **Approval.** Approve as yourself: refused (approver cannot be the person who ran L3). Approve as someone else with a change id: approved, with the script fingerprint.
7. **Audit trail.** Every step, who and when.

Say plainly: the Gosu is generated, checked and approved here, but not executed; the checks are rules, not an AI opinion.
