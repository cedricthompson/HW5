// Calls to the FastAPI backend. Start it from backend/ with:
//   uvicorn main:app --reload --port 8000

import type {
  ApprovalRequest, ApproveResponse, Cash, EventsResponse, RunResponse, TicketDetail, TicketsResponse,
} from "./types";

// The FastAPI backend. Its CORS settings allow this page's origin (http://localhost:5173).
export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : `${res.status} ${res.statusText}`);
  }
  return body as T;
}

export const api = {
  tickets: () => call<TicketsResponse>("/tickets"),
  ticket: (id: number) => call<TicketDetail>(`/tickets/${id}`),
  run: (id: number) => call<RunResponse>(`/tickets/${id}/run`, { method: "POST" }),
  events: (params: { after?: string; limit?: number; run_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.after) q.set("after", params.after);
    if (params.limit) q.set("limit", String(params.limit));
    if (params.run_id) q.set("run_id", params.run_id);
    return call<EventsResponse>(`/events?${q}`);
  },
  approvals: (status = "pending") =>
    call<{ requests: ApprovalRequest[] }>(`/approvals?status=${encodeURIComponent(status)}`),
  approve: (id: number, approvedBy: string) =>
    call<ApproveResponse>(`/approvals/${id}/approve`, {
      method: "POST", body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: number, rejectedBy: string, reason: string) =>
    call<{ request_id: number; status: string }>(`/approvals/${id}/reject`, {
      method: "POST", body: JSON.stringify({ rejected_by: rejectedBy, reason }),
    }),
  cash: () => call<Cash>("/cash"),
  reset: () => call<{ reset: boolean }>("/reset", { method: "POST" }),
};
