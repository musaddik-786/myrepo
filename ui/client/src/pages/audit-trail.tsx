import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { getFixAudit } from "@/lib/api";
import type { FixAuditRow } from "@/lib/types";

export default function AuditTrail() {
  const [rows, setRows] = useState<FixAuditRow[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getFixAudit().then(setRows).catch((e) => setError(e.message)); }, []);
  return (
    <AppShell active="Audit trail" title="Audit trail" subtitle="Every L1, L2 and L3 run, approval and rejection, with who did it.">
      {error && <p className="text-destructive">{error}</p>}
      {rows && rows.length === 0 && <p className="text-muted-foreground">No activity yet. Open a ticket and run a stage.</p>}
      {rows && rows.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-muted/60"><tr className="text-left text-xs uppercase text-muted-foreground">
              <th className="px-4 py-3">When</th><th>Ticket</th><th>Action</th><th>By</th><th>Detail</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-border align-top">
                  <td className="whitespace-nowrap px-4 py-3">{r.created_at ? new Date(r.created_at).toLocaleString() : "this session"}</td>
                  <td className="pr-4">#{r.ticket_id}</td>
                  <td className="pr-4"><span className={r.action === "approved" ? "rounded bg-green-100 px-2 py-0.5 text-green-800" : r.action === "rejected" ? "rounded bg-red-100 px-2 py-0.5 text-red-800" : "rounded bg-muted px-2 py-0.5"}>{r.action}</span></td>
                  <td className="pr-4">{r.actor ?? "—"}</td>
                  <td className="pr-4 font-mono text-xs text-muted-foreground">{Object.entries(r.detail).map(([k, v]) => `${k}: ${String(v).slice(0, 24)}`).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
