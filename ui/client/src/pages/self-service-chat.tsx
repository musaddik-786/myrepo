import { useRef, useState } from "react";
import { Check, Loader2, Send } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createL0Ticket, l0Chat, setL0Outcome, type L0Reply } from "@/lib/api";

type Turn = { role: "user" | "assistant"; content: string; reply?: L0Reply };

export default function SelfServiceChat() {
  const session = useRef(`l0-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [resolved, setResolved] = useState(false);
  const [ticketNo, setTicketNo] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const last = [...turns].reverse().find((t) => t.reply)?.reply;

  const send = async () => {
    if (!text.trim()) { setError("Describe what is going wrong first."); return; }
    const next: Turn[] = [...turns, { role: "user", content: text.trim() }];
    setTurns(next); setText(""); setError(""); setBusy(true);
    try {
      const reply = await l0Chat(next.map(({ role, content }) => ({ role, content })), session.current);
      setTurns([...next, { role: "assistant", content: reply.reply, reply }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally { setBusy(false); }
  };

  const solved = async () => {
    await setL0Outcome(session.current, "resolved").catch(() => undefined);
    setResolved(true);
  };

  const raise = async () => {
    if (!last) return;
    if (!name.trim() || !email.trim()) { setError("Enter your name and email so support can reach you."); return; }
    setBusy(true); setError("");
    try {
      const r = await createL0Ticket({ session_id: session.current, name, email, title: last.ticket_draft.title,
        description: last.ticket_draft.description, module: last.module });
      setTicketNo(r.ticket_number);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the ticket");
    } finally { setBusy(false); }
  };

  return (
    <AppShell active="Self-service chat" title="Self-service support (L0)"
      subtitle="Describe the problem. Known issues get safe next steps; anything else becomes a ticket for the support team.">
      <div className="mx-auto max-w-[760px] space-y-4">
        <div className="space-y-3 rounded-lg border border-border bg-card p-5 shadow-sm">
          {turns.length === 0 && <p className="text-sm text-muted-foreground">Try: "Our GL final audit shows a credit but payroll went up".</p>}
          {turns.map((t, i) => (
            <div key={i} className={t.role === "user" ? "ml-12 rounded-lg bg-primary/10 p-3 text-sm" : "mr-12 rounded-lg border border-border bg-background p-3 text-sm"}>
              <p>{t.content}</p>
              {t.reply && t.reply.steps.length > 0 && <ol className="mt-2 list-decimal space-y-1 pl-5">{t.reply.steps.map((s) => <li key={s}>{s}</li>)}</ol>}
              {t.reply && t.reply.ask_for.length > 0 && (
                <div className="mt-2 rounded-md bg-amber-50 p-2 text-amber-900"><b>Please tell us:</b>
                  <ul className="list-disc pl-5">{t.reply.ask_for.map((s) => <li key={s}>{s}</li>)}</ul></div>
              )}
            </div>
          ))}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        {last && !resolved && !ticketNo && (
          <div className="space-y-3 rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-sm font-medium">Did this solve it?</span>
              <Button variant="outline" onClick={solved}><Check className="mr-2 h-4 w-4" />Yes, solved without a ticket</Button>
            </div>
            <div className="border-t border-border pt-3 text-sm">
              <div className="mb-2 font-medium">No, raise a ticket</div>
              <p className="mb-2 rounded-md bg-muted p-2 text-xs">{last.ticket_draft.title}</p>
              <div className="flex flex-wrap gap-2">
                <Input className="w-48" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
                <Input className="w-64" type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                <Button onClick={raise} disabled={busy}>{busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Create ticket in osTicket</Button>
              </div>
            </div>
          </div>
        )}
        {resolved && <p className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-900">Glad that helped. Counted as resolved without a ticket.</p>}
        {ticketNo && <p className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-900">Ticket <b>#{ticketNo}</b> created in osTicket with your details and the matched module.</p>}

        {!resolved && !ticketNo && (
          <div className="flex gap-2">
            <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={turns.length ? "Reply with the details asked for above, or add more information" : "Describe the problem"} rows={turns.length ? 2 : 3} className="bg-card" />
            <Button onClick={send} disabled={busy} aria-label="Send">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
