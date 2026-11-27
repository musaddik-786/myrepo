import { useState } from "react";
import { Loader2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { findSimilarTickets } from "@/lib/api";
import type { SimilarResult } from "@/lib/types";

interface Props {
  ticketId: string;
  query: { title?: string; description?: string; module?: string; severity?: string; created?: string };
  /** Persisted outputs.similar -- either from this panel's own button or from the Orchestrator Agent's L1 run. */
  result: SimilarResult | undefined;
  /** True while the Orchestrator Agent's own L1 run is in progress (it also calls this same agent as one of its steps). */
  loading?: boolean;
}

const strengthVariant = (s: string): "default" | "secondary" | "outline" =>
  s.toLowerCase() === "strong" ? "default" : s.toLowerCase() === "moderate" ? "secondary" : "outline";

export function SimilarTicketsPanel({ ticketId, query, result, loading = false }: Props) {
  const [manual, setManual] = useState<SimilarResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    setSearching(true);
    setError(null);
    findSimilarTickets(ticketId, query)
      .then(setManual)
      .catch((e: Error) => setError(e.message))
      .finally(() => setSearching(false));
  };

  const display = manual ?? result;
  const hasText = Boolean(query.title?.trim() || query.description?.trim());

  return (
    <div className="space-y-4 rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-sm font-semibold text-[#0B2A4A]">Similar historical tickets</h2>
        <Button type="button" variant="outline" size="sm" onClick={run} disabled={searching || loading || !hasText}>
          {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          {display ? "Refresh" : "Find similar tickets"}
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">Could not search for similar tickets: {error}</p>}
      {loading && !display && <p className="text-sm text-muted-foreground">Running the L1 guide's own similar-ticket search…</p>}

      {display && display.no_confident_match && (
        <p className="text-sm text-muted-foreground">
          No confident match found. {display.suggested_next_step}
        </p>
      )}

      {display && (display.matches?.length ?? 0) > 0 && (
        <ul className="space-y-4">
          {display.matches.map((m) => (
            <li key={m.id} className="space-y-3 rounded-md border border-border bg-muted/30 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-semibold">
                  #{m.rank} · {m.id}
                </span>
                <Badge variant={strengthVariant(m.match_strength)}>{m.match_strength}</Badge>
                {m.ticket.system && <Badge variant="outline">{m.ticket.system}</Badge>}
              </div>
              {m.ticket.description && (
                <p className="line-clamp-3 text-sm text-foreground/90">{m.ticket.description}</p>
              )}
              <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                <div><dt className="font-medium">Why similar</dt><dd className="text-muted-foreground">{m.why_similar}</dd></div>
                <div><dt className="font-medium">What differs</dt><dd className="text-muted-foreground">{m.what_differs}</dd></div>
                <div><dt className="font-medium">Reusable resolution</dt><dd className="text-muted-foreground">{m.reusable_info}{m.ticket.resolution ? ` — ${m.ticket.resolution}` : ""}</dd></div>
                {m.ticket.rca && <div><dt className="font-medium">RCA</dt><dd className="text-muted-foreground">{m.ticket.rca}</dd></div>}
              </dl>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
