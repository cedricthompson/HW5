import { AGENTS, STATUS_LABEL, agentName } from "../agents";
import type { AgentName, AgentReport, RunResponse } from "../types";
import { Icon } from "./Icon";

interface Props {
  ticketId: number;
  result: RunResponse | null;
  reports: { agent: AgentName; report: AgentReport; alert: boolean }[];
  pendingCount: number;
  onGoToApprovals: () => void;
}

export function RunSummary({ ticketId, result, reports, pendingCount, onGoToApprovals }: Props) {
  const ticketReports = reports.filter((r) => !r.alert);
  const alert = reports.find((r) => r.alert)?.report ?? result?.bills_alert ?? null;
  const boss = result?.decision ?? ticketReports.find((r) => r.agent === "boss")?.report ?? null;
  const helpers = AGENTS.filter((a) => a.id !== "boss")
    .map((a) => ({ a, r: ticketReports.filter((x) => x.agent === a.id).at(-1)?.report }))
    .filter((x) => x.r);
  const notCalled = AGENTS.filter((a) => a.id !== "boss" && !helpers.some((h) => h.a.id === a.id));

  if (!boss && helpers.length === 0) return null;

  return (
    <section className="panel summary">
      <div className="panel-head">
        <h2>What the team did · ticket #{ticketId}</h2>
        {boss?.ticket_status && <span className={`status s-${boss.ticket_status}`}>{STATUS_LABEL[boss.ticket_status] ?? boss.ticket_status}</span>}
      </div>

      {alert && (
        <div className="alert-box">
          <Icon name="bolt" />
          <div><strong>Bills-due alert (before the ticket):</strong> {alert.final_call ?? alert.summary}</div>
        </div>
      )}

      {boss && (
        <div className="boss-call">
          <div className="boss-tag">Boss · final call</div>
          <p className="boss-final">{boss.final_call ?? boss.summary}</p>
          {boss.human_next_step && (
            <div className="next-step">
              <span><strong>Your next step:</strong> {boss.human_next_step}</span>
              {pendingCount > 0 && (
                <button className="btn btn-gold" onClick={onGoToApprovals}>
                  Review {pendingCount} approval{pendingCount > 1 ? "s" : ""} <Icon name="arrow" size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <div className="did-grid">
        {helpers.map(({ a, r }, i) => (
          <article key={a.id} className={`did a-${a.id}`} style={{ animationDelay: `${i * 110}ms` }}>
            <header><span className="did-dot" />{a.name}</header>
            <p>{r!.summary}</p>
            {r!.actions_taken.length > 0 && (
              <ul>{r!.actions_taken.slice(0, 3).map((x) => <li key={x}>{x}</li>)}</ul>
            )}
            {(r!.approval_request_ids.length > 0 || r!.draft_ids.length > 0) && (
              <div className="did-tags">
                {r!.approval_request_ids.map((id) => <span key={`r${id}`} className="chip gold">Request #{id}</span>)}
                {r!.draft_ids.map((id) => <span key={`d${id}`} className="chip">Draft #{id}</span>)}
              </div>
            )}
          </article>
        ))}
      </div>

      {notCalled.length > 0 && (
        <p className="muted small not-called">
          Not called: {notCalled.map((a) => agentName(a.id)).join(", ")}. Boss sent the ticket only to the people who owned a part of it.
        </p>
      )}
    </section>
  );
}
