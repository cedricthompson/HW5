import { money } from "../agents";
import type { Cash } from "../types";
import { useCountUp } from "../useCountUp";
import { Icon } from "./Icon";

export function CashCard({ cash, flash }: { cash: Cash | null; flash: number }) {
  const shown = useCountUp(cash?.balance ?? null);
  return (
    <section className="panel cash" key={flash} data-flash={flash > 0 ? "yes" : "no"}>
      <div className="cash-head">
        <Icon name="bank" />
        <span>Checking balance</span>
      </div>
      <div className="cash-amount">{money(shown)}</div>
      <div className="cash-meta">
        <span>as of {cash?.as_of ?? "—"}</span>
        <span>Waiting on approval: <b>{money(cash?.pending_requests_total)}</b></span>
        <span>If all approved: <b>{money(cash?.balance_if_all_pending_paid)}</b></span>
      </div>
      {cash && cash.payments_made.length > 0 && (
        <ul className="payments">
          {cash.payments_made.slice().reverse().map((p) => (
            <li key={p.id}>
              <span>{p.kind === "invoice" ? `Invoice ${p.ref_id}` : p.kind === "rent" ? `Rent (lease ${p.ref_id})` : `Purchase order`}</span>
              <span className="neg">−{money(p.amount)}</span>
              <small>approved by {p.approved_by} · {p.paid_at}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
