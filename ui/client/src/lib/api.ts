// import { mapTicketRow, type KbResolveResult, type SimilarQuery, type SimilarResult, type Ticket, type TicketRecordRow } from "./types";

// async function getJson<T>(url: string): Promise<T> {
//   const res = await fetch(url);
//   if (!res.ok) {
//     const body = await res.json().catch(() => ({}));
//     throw new Error(body.error || `Request to ${url} failed with ${res.status}`);
//   }
//   return res.json();
// }

// export async function fetchTickets(): Promise<Ticket[]> {
//   const rows = await getJson<TicketRecordRow[]>("/api/tickets");
//   return rows.map(mapTicketRow);
// }

// export async function fetchModules(): Promise<string[]> {
//   return getJson<string[]>("/api/modules");
// }

// export async function fetchAssigneeTeams(): Promise<string[]> {
//   return getJson<string[]>("/api/assignee-teams");
// }

// export async function fetchSimilarTickets(query: SimilarQuery): Promise<SimilarResult> {
//   const res = await fetch("/api/tickets/similar", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(query),
//   });
//   if (!res.ok) {
//     const body = await res.json().catch(() => ({}));
//     throw new Error(body.detail || body.error || `Similar-ticket search failed (${res.status})`);
//   }
//   return res.json();
// }

// export async function resolveKbCard(query: { id?: string; title?: string; description?: string }): Promise<KbResolveResult> {
//   const res = await fetch("/api/kb/resolve", {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(query),
//   });
//   if (!res.ok) {
//     const body = await res.json().catch(() => ({}));
//     throw new Error(body.detail || body.error || `Suggested-fix lookup failed (${res.status})`);
//   }
//   return res.json();
// }

// async function fixCall<T>(path: string, init?: RequestInit): Promise<T> {
//   const res = await fetch(`/api/fix${path}`, { headers: { "Content-Type": "application/json" }, ...init });
//   if (!res.ok) {
//     const body = await res.json().catch(() => ({}));
//     throw new Error(body.detail || body.error || `Request failed (${res.status})`);
//   }
//   return res.json();
// }

// export const getFixRun = (id: string) => fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}`);
// export const runFixStage = (id: string, stage: "l1" | "l2" | "l3", t: { title: string; description: string }, user: string) =>
//   fixCall<{ source: string }>(`/${encodeURIComponent(id)}/run/${stage}`, { method: "POST", body: JSON.stringify({ ...t, user }) });
// export const decideFix = (id: string, kind: "approve" | "reject", body: { approver: string; change_id: string; note?: string }) =>
//   fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}/${kind}`, { method: "POST", body: JSON.stringify(body) });
// export const resolveFix = (id: string, body: { level: string; resolution_type: string; notes: string; resolved_by: string }) =>
//   fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}/resolve`, { method: "POST", body: JSON.stringify(body) });
// export const getFixAudit = () => fixCall<import("./types").FixAuditRow[]>("/audit");

// export interface L0Reply {
//   reply: string;
//   module: string | null;
//   steps: string[];
//   ask_for: string[];
//   matched_card: string | null;
//   ticket_draft: { title: string; description: string };
// }
// export async function l0Chat(messages: { role: "user" | "assistant"; content: string }[], session_id: string): Promise<L0Reply> {
//   const res = await fetch("/api/l0/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages, session_id }) });
//   if (!res.ok) {
//     const body = await res.json().catch(() => ({}));
//     throw new Error(body.detail || `Chat failed (${res.status})`);
//   }
//   return res.json();
// }

// export const getL0Stats = async (): Promise<{ chats: number; resolved_without_ticket: number; tickets_created: number; deflection_rate: number }> => {
//   const res = await fetch("/api/l0/stats");
//   if (!res.ok) throw new Error(`Stats failed (${res.status})`);
//   return res.json();
// };
// export const setL0Outcome = (session_id: string, outcome: "resolved" | "ticket_created" | "open") =>
//   fetch("/api/l0/outcome", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id, outcome }) });
// export async function createL0Ticket(body: { session_id: string; name: string; email: string; title: string; description: string; module: string | null }): Promise<{ ticket_number: string }> {
//   const res = await fetch("/api/l0/ticket", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
//   if (!res.ok) {
//     const e = await res.json().catch(() => ({}));
//     throw new Error(e.detail || `Could not create the ticket (${res.status})`);
//   }
//   return res.json();
// }



import { mapTicketRow, type ClassificationResult, type KbResolveResult, type SimilarQuery, type SimilarResult, type Ticket, type TicketRecordRow } from "./types";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request to ${url} failed with ${res.status}`);
  }
  return res.json();
}

export async function fetchTickets(): Promise<Ticket[]> {
  const rows = await getJson<TicketRecordRow[]>("/api/tickets");
  return rows.map(mapTicketRow);
}

export async function fetchModules(): Promise<string[]> {
  return getJson<string[]>("/api/modules");
}

export async function fetchAssigneeTeams(): Promise<string[]> {
  return getJson<string[]>("/api/assignee-teams");
}

export async function classifyTicket(recordId: string): Promise<ClassificationResult> {
  // Routed through the Orchestrator Agent -> Ticket Classification & Triage Agent.
  const res = await fetch(`/api/orchestrator/classify/${encodeURIComponent(recordId)}`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Classification failed (${res.status})`);
  }
  return res.json();
}

export async function fetchSimilarTickets(query: SimilarQuery): Promise<SimilarResult> {
  const res = await fetch("/api/tickets/similar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(query),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Similar-ticket search failed (${res.status})`);
  }
  return res.json();
}

export async function resolveKbCard(query: { id?: string; title?: string; description?: string }): Promise<KbResolveResult> {
  const res = await fetch("/api/kb/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(query),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Suggested-fix lookup failed (${res.status})`);
  }
  return res.json();
}

// Approve/Reject/Resolve stay plain REST, through app/routers/orchestrator.py
// (which itself now calls the real agent MCP server over HTTP) -- no LLM
// decision needed for a form-driven action, same split the claims-solution
// reference project uses (its decideApproval never goes through its
// orchestrator's /chat either).
async function fixCall<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/orchestrator${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export const getFixRun = (id: string) => fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}`);

// L1/L2/L3 "run" actions go through the real, standalone Orchestrator
// Agent process's /chat (proxied at /orchestrator-agent -- see
// ui/vite.config.ts) -- a real network call reaching a real running agent
// process, which decides which domain agent's tool(s) to call and persists
// the result itself. The chat reply text is discarded (same pattern as the
// claims-solution reference project): we just re-fetch the ticket's run
// state afterward via getFixRun above to display it.
interface ChatStreamOptions {
  onToolEvent?: (tool: string, state: "Starting" | "Done") => void;
}

const TOOL_EVENT_RE = /\[Tool:\s*([^\]]+)\]\s*(Starting|Done)/g;

async function streamOrchestratorChat(message: string, opts: ChatStreamOptions = {}): Promise<string> {
  const resp = await fetch("/orchestrator-agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history: [] }),
  });
  if (!resp.ok || !resp.body) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Orchestrator agent request failed (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  const processLine = (line: string) => {
    if (!line.startsWith("data:")) return;
    const chunk = line.slice(5).replace(/^ /, "").replace(/\r$/, "");
    if (!chunk || chunk === "[DONE]") return;
    for (const match of chunk.matchAll(TOOL_EVENT_RE)) {
      opts.onToolEvent?.(match[1].trim(), match[2] as "Starting" | "Done");
    }
    full += chunk;
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) processLine(line);
  }
  if (buffer) processLine(buffer);
  return full;
}

// Title/description are sent in the message itself -- the domain tools
// (match_kb_card, collect_l1_info, diagnose, author_remediation) take them
// as plain arguments, and the orchestrator has no other way to know a
// ticket's text (get_ticket_run only carries prior STAGE outputs, not the
// ticket's own title/description).
const STAGE_MESSAGE: Record<"l1" | "l2" | "l3", (id: string, t: { title: string; description: string }, user: string) => string> = {
  l1: (id, t) => `Run the L1 guide for ticket ${id}. Title: ${JSON.stringify(t.title)}. Description: ${JSON.stringify(t.description)}.`,
  l2: (id, t) => `Continue to L2 diagnosis for ticket ${id}. Title: ${JSON.stringify(t.title)}. Description: ${JSON.stringify(t.description)}.`,
  l3: (id, t, user) => `Escalate ticket ${id} to L3 data fix. Title: ${JSON.stringify(t.title)}. Description: ${JSON.stringify(t.description)}. Run by: ${user}.`,
};

export async function runFixStage(
  id: string, stage: "l1" | "l2" | "l3", t: { title: string; description: string }, user: string,
): Promise<{ source: string }> {
  await streamOrchestratorChat(STAGE_MESSAGE[stage](id, t, user));
  return { source: "ai" };
}

export const decideFix = (id: string, kind: "approve" | "reject", body: { approver: string; change_id: string; note?: string }) =>
  fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}/${kind}`, { method: "POST", body: JSON.stringify(body) });
export const resolveFix = (id: string, body: { level: string; resolution_type: string; notes: string; resolved_by: string }) =>
  fixCall<import("./types").FixRun>(`/${encodeURIComponent(id)}/resolve`, { method: "POST", body: JSON.stringify(body) });
export const getFixAudit = () => fixCall<import("./types").FixAuditRow[]>("/audit");

// Similar Incident Retrieval Agent, triggered directly by its own button --
// deliberately NOT routed through the Orchestrator Agent's /chat (unlike the
// L1 guide, which also calls this same agent as one of its own steps). The
// result is persisted into the ticket's outputs.similar on the backend, so
// it shows up the same way either path produced it.
export const findSimilarTickets = (
  ticketId: string,
  query: { title?: string; description?: string; module?: string; severity?: string; created?: string },
) => fixCall<import("./types").SimilarResult>(`/similar/${encodeURIComponent(ticketId)}`, { method: "POST", body: JSON.stringify(query) });

export interface L0Reply {
  reply: string;
  module: string | null;
  steps: string[];
  ask_for: string[];
  matched_card: string | null;
  ticket_draft: { title: string; description: string };
}

// Extracts the first balanced {...} object out of the agent's raw streamed
// text (it may be followed by a trailing "End" marker -- see
// agents/l0_self_service/server.py's SYSTEM_PROMPT).
function extractJsonObject(text: string): L0Reply {
  const start = text.indexOf("{");
  if (start === -1) throw new Error("The L0 agent did not return a structured reply.");
  let depth = 0;
  for (let i = start; i < text.length; i++) {
    if (text[i] === "{") depth++;
    else if (text[i] === "}") {
      depth--;
      if (depth === 0) return JSON.parse(text.slice(start, i + 1));
    }
  }
  throw new Error("The L0 agent's reply was cut off before it finished.");
}

// Reconstructs the conversation as plain text for the agent's own /chat,
// which (like the Orchestrator Agent's /chat) only takes a single message
// per request -- the agent itself re-parses this back into role/content
// turns per its own SYSTEM_PROMPT.
function formatL0Message(messages: { role: "user" | "assistant"; content: string }[], session_id: string): string {
  const convo = messages.map((m) => `${m.role}: ${m.content}`).join("\n");
  return `Session: ${session_id}\n${convo}`;
}

export async function l0Chat(messages: { role: "user" | "assistant"; content: string }[], session_id: string): Promise<L0Reply> {
  // Routed to the real, standalone L0 Self-Service Agent process's /chat
  // (proxied at /l0-agent -- see ui/vite.config.ts), same real-process
  // pattern as the Orchestrator Agent above, not the old in-process call.
  const resp = await fetch("/l0-agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: formatL0Message(messages, session_id) }),
  });
  if (!resp.ok || !resp.body) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Chat failed (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  const processLine = (line: string) => {
    if (!line.startsWith("data:")) return;
    const chunk = line.slice(5).replace(/^ /, "").replace(/\r$/, "");
    if (!chunk || chunk === "[DONE]" || chunk.startsWith("[Tool:")) return;
    if (chunk.startsWith("[AGENT_ERROR]")) throw new Error("The L0 agent hit an internal error -- check its terminal for details.");
    full += chunk;
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) processLine(line);
  }
  if (buffer) processLine(buffer);
  return extractJsonObject(full);
}

export const getL0Stats = async (): Promise<{ chats: number; resolved_without_ticket: number; tickets_created: number; deflection_rate: number }> => {
  const res = await fetch("/api/l0/stats");
  if (!res.ok) throw new Error(`Stats failed (${res.status})`);
  return res.json();
};
export const setL0Outcome = (session_id: string, outcome: "resolved" | "ticket_created" | "open") =>
  fetch("/api/l0/outcome", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id, outcome }) });
export async function createL0Ticket(body: { session_id: string; name: string; email: string; title: string; description: string; module: string | null }): Promise<{ ticket_number: string }> {
  const res = await fetch("/api/l0/ticket", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `Could not create the ticket (${res.status})`);
  }
  return res.json();
}