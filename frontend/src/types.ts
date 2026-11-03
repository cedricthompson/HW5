// Shapes returned by the FastAPI backend (backend/main.py).

export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  state: "open" | "resolved";
  notes: string | null;
  created_at: string;
}

export interface TicketsResponse {
  date_today: string;
  tickets: Ticket[];
}

export interface Fact {
  fact: string;
  source_tool: string;
}

export interface AgentReport {
  agent: AgentName;
  ticket_id: number | null;
  summary: string;
  facts: Fact[];
  actions_taken: string[];
  approval_request_ids: number[];
  draft_ids: number[];
  blockers: string[];
  recommendation: string;
  // Boss only
  final_call?: string;
  ticket_status?: string | null;
  human_next_step?: string;
}

export interface Draft {
  id: number;
  ticket_id: number;
  recipient: string;
  subject: string;
  body: string;
  author: string;
  status: string;
  created_at: string;
}

export interface ApprovalRequest {
  id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number | null;
  ticket_id: number | null;
  vendor_id: number | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
  amount: number;
  reason: string;
  requested_by: string;
  status: string;
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  payment_id: number | null;
  expected_arrival: string | null;
}

export interface TicketDetail extends Omit<Ticket, "state"> {
  date_today: string;
  drafts: Draft[];
  approval_requests: ApprovalRequest[];
  updates: { id: number; old_status: string; new_status: string; note: string; updated_by: string; created_at: string }[];
}

export interface RunResponse {
  run_id: string;
  ticket_id: number;
  bills_alert: AgentReport | null;
  decision: AgentReport;
  ticket: TicketDetail;
}

export type EventKind =
  | "run_start" | "model_response" | "tool_call" | "tool_result"
  | "delegation" | "guardrail" | "run_end" | "error";

export interface AgentEvent {
  timestamp: string;
  run_id: string;
  ticket_id: number | null;
  agent: AgentName;
  parent_agent: AgentName | null;
  depth: number;
  event: EventKind;
  said?: string | null;
  tools?: string[];
  tool?: string;
  args?: Record<string, unknown>;
  output?: unknown;
  to?: AgentName;
  report?: AgentReport;
  detail?: Record<string, unknown>;
  usage?: { requests?: number; tool_calls?: number; total_tokens?: number };
}

export interface EventsResponse {
  count: number;
  total_events: number;
  events: AgentEvent[];
}

export interface Payment {
  id: number;
  kind: string;
  ref_id: number;
  amount: number;
  account: string;
  paid_at: string;
  approved_by: string;
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  pending_requests_total: number;
  balance_if_all_pending_paid: number;
  payments_made: Payment[];
}

export interface ApproveResponse {
  result: {
    request_id: number;
    paid: boolean;
    status?: string;
    amount: number;
    balance_before?: number;
    balance_after?: number;
    note?: string;
  };
  cash: Cash;
}
