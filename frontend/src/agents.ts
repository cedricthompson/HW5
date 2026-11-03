// The agent team, and how each audit event is shown on the board.

import type { AgentEvent, AgentName, AgentReport } from "./types";

export interface AgentInfo {
  id: AgentName;
  name: string;
  role: string;
  initials: string;
}

export const AGENTS: AgentInfo[] = [
  { id: "boss", name: "Boss", role: "Reads the board, routes work, makes the final call", initials: "BO" },
  { id: "accounting", name: "Accounting", role: "Cash, bills, and payments for approval", initials: "AC" },
  { id: "inventory", name: "Inventory", role: "Stock by SKU and size, vendors, restock", initials: "IN" },
  { id: "facilities", name: "Facilities", role: "Lease, rent, and a clean store", initials: "FA" },
  { id: "customer_service", name: "Customer Service", role: "Drafts to customers (never sent)", initials: "CS" },
];

export const agentName = (id: AgentName | null | undefined) =>
  AGENTS.find((a) => a.id === id)?.name ?? (id ?? "");

// Plumbing tool calls that don't need their own line on the board.
const HIDDEN_TOOLS = new Set(["final_result", "ask_teammate"]);

export type Phase = "idle" | "working" | "waiting" | "done" | "error";

export interface AgentLive {
  phase: Phase;
  line: string;
  tools: string[];
  waitingOn?: AgentName;
}

export function fmtArgs(args?: Record<string, unknown>): string {
  if (!args) return "";
  return Object.entries(args)
    .filter(([k]) => !["requested_by", "updated_by", "author", "created_by"].includes(k))
    .map(([k, v]) => `${k}: ${typeof v === "string" && v.length > 40 ? v.slice(0, 40) + "…" : String(v)}`)
    .join(", ");
}

export function fmtOutput(out: unknown): string {
  if (out == null) return "";
  if (typeof out === "string") return out.length > 160 ? out.slice(0, 160) + "…" : out;
  if (Array.isArray(out)) return `${out.length} item(s)`;
  if (typeof out === "object") {
    const entries = Object.entries(out as Record<string, unknown>)
      .filter(([, v]) => v === null || ["string", "number", "boolean"].includes(typeof v))
      .slice(0, 5)
      .map(([k, v]) => `${k}: ${v}`);
    const lists = Object.entries(out as Record<string, unknown>)
      .filter(([, v]) => Array.isArray(v))
      .map(([k, v]) => `${k}: ${(v as unknown[]).length}`);
    return [...entries, ...lists].join(" · ");
  }
  return String(out);
}

/** One line for the activity feed, or null if the event is plumbing. */
export function describe(e: AgentEvent): { kind: string; text: string; sub?: string } | null {
  switch (e.event) {
    case "run_start":
      return e.depth === 0
        ? { kind: "start", text: e.ticket_id == null ? "Bills-due check started" : `Started ticket ${e.ticket_id}`, sub: e.said ?? undefined }
        : { kind: "start", text: `Picked up the handoff from ${agentName(e.parent_agent)}`, sub: e.said ?? undefined };
    case "model_response":
      return e.said ? { kind: "said", text: e.said } : null;
    case "tool_call":
      if (!e.tool || HIDDEN_TOOLS.has(e.tool)) return null;
      return { kind: "tool", text: e.tool, sub: fmtArgs(e.args) };
    case "tool_result":
      if (!e.tool || HIDDEN_TOOLS.has(e.tool)) return null;
      return { kind: "result", text: `${e.tool} returned`, sub: fmtOutput(e.output) };
    case "delegation":
      return { kind: "handoff", text: `Handed off to ${agentName(e.to)}`, sub: e.said ?? undefined };
    case "guardrail":
      return { kind: "guard", text: "Guardrail", sub: e.said ?? undefined };
    case "run_end":
      return { kind: "done", text: "Finished", sub: e.said ?? undefined };
    case "error":
      return { kind: "error", text: "Error", sub: e.said ?? undefined };
    default:
      return null;
  }
}

/** Where each agent is right now, worked out from the run's events (oldest first). */
export function liveState(events: AgentEvent[]): Record<AgentName, AgentLive> {
  const state = Object.fromEntries(
    AGENTS.map((a) => [a.id, { phase: "idle", line: "Waiting for work", tools: [] } as AgentLive]),
  ) as Record<AgentName, AgentLive>;
  for (const e of events) {
    const s = state[e.agent];
    if (!s) continue;
    switch (e.event) {
      case "run_start":
        s.phase = "working";
        s.waitingOn = undefined;
        s.line = e.depth === 0 ? "Reading the board" : `Asked by ${agentName(e.parent_agent)}`;
        break;
      case "tool_call":
        if (e.tool === "ask_teammate") break;
        if (e.tool && e.tool !== "final_result" && !s.tools.includes(e.tool)) s.tools.push(e.tool);
        s.line = e.tool === "final_result" ? "Writing the report" : `Using ${e.tool}`;
        break;
      case "tool_result":
        if (e.tool === "ask_teammate") {
          s.phase = "working";
          s.waitingOn = undefined;
          s.line = "Got the teammate's report";
        }
        break;
      case "delegation":
        s.phase = "waiting";
        s.waitingOn = e.to;
        s.line = `Waiting on ${agentName(e.to)}`;
        break;
      case "model_response":
        if (e.said) s.line = e.said;
        break;
      case "guardrail":
        s.line = `Guardrail: ${e.said ?? ""}`;
        break;
      case "run_end":
        s.phase = "done";
        s.waitingOn = undefined;
        s.line = e.said ?? "Done";
        break;
      case "error":
        s.phase = "error";
        s.line = e.said ?? "Error";
        break;
    }
  }
  return state;
}

/** The handoff path in the order it happened, e.g. Boss → Accounting → Inventory → Customer Service. */
export function handoffs(events: AgentEvent[]): { from: AgentName; to: AgentName }[] {
  return events
    .filter((e) => e.event === "delegation" && e.to)
    .map((e) => ({ from: e.agent, to: e.to as AgentName }));
}

/** Each agent's finished report from the run (ticket work, not the bills alert). */
export function reports(events: AgentEvent[]): { agent: AgentName; report: AgentReport; alert: boolean }[] {
  return events
    .filter((e) => e.event === "run_end" && e.report)
    .map((e) => ({ agent: e.agent, report: e.report as AgentReport, alert: e.depth === 0 && e.ticket_id == null }));
}

export const money = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export const TICKET_TYPES: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Discount request",
};

export const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  in_progress: "In progress",
  waiting_on_approval: "Waiting on approval",
  waiting_on_vendor: "Waiting on vendor",
  resolved: "Resolved",
  declined: "Declined",
};
