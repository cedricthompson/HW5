import { forwardRef, useState } from "react";
import { money } from "../agents";
import type { ApprovalRequest } from "../types";
import { Icon } from "./Icon";

interface Props {
  requests: ApprovalRequest[];
  approver: string;
  setApprover: (name: string) => void;
  busy: boolean;
  onApprove: (r: ApprovalRequest) => Promise<void>;
  onReject: (r: ApprovalRequest) => Promise<void>;
}

const KIND_LABEL = { invoice: "Vendor invoice", rent: "Rent", purchase_order: "Purchase order" };

export const Approvals = forwardRef<HTMLElement, Props>(function Approvals(
  { requests, approver, setApprover, busy, onApprove, onReject }, ref,
) {
  const [working, setWorking] = useState<number | null>(null);
  const act = async (r: ApprovalRequest, fn: (r: ApprovalRequest) => Promise<void>) => {
    setWorking(r.id);
    try { await fn(r); } finally { setWorking(null); }
  };

  return (
    <section className={`panel approvals ${requests.length ? "needs" : ""}`} ref={ref}>
      <div className="panel-head">
        <h2>Approvals</h2>
        {requests.length > 0 ? <span className="needs-you">Needs you · {requests.length}</span> : <span className="muted small">Nothing waiting</span>}
      </div>
      <p className="muted small">Agents only prepare payments. Money moves when a person approves here.</p>
      <label className="approver">
        <span>Approving as</span>
        <input value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="Your name" />
      </label>
      <div className="req-list">
        {requests.map((r, i) => (
          <article key={r.id} className="req" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="req-top">
              <span className="req-kind">{KIND_LABEL[r.kind] ?? r.kind}</span>
              <span className="req-amt">{money(r.amount)}</span>
            </div>
            <p className="req-reason">{r.reason}</p>
            <p className="muted small">
              Request #{r.id} · ticket #{r.ticket_id} · prepared by {r.requested_by}
              {r.kind === "purchase_order" && r.qty ? ` · ${r.qty} × ${r.sku} ${r.size}` : ""}
            </p>
            <div className="req-actions">
              <button className="btn btn-approve" disabled={busy || !approver.trim() || working !== null} onClick={() => act(r, onApprove)}>
                {working === r.id ? <span className="spinner" /> : <Icon name="check" size={14} />} Approve & pay
              </button>
              <button className="btn btn-ghost" disabled={busy || !approver.trim() || working !== null} onClick={() => act(r, onReject)}>
                <Icon name="x" size={14} /> Reject
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
});
