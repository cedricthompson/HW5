import { STATUS_LABEL, TICKET_TYPES } from "../agents";
import type { Ticket } from "../types";
import { Icon, TYPE_ICON } from "./Icon";

interface Props {
  tickets: Ticket[];
  selected: number | null;
  running: number | null;
  resolved: Set<number>;
  onSelect: (id: number) => void;
  onRun: (id: number) => void;
}

export function TicketList({ tickets, selected, running, resolved, onSelect, onRun }: Props) {
  return (
    <section className="panel tickets">
      <div className="panel-head">
        <h2>Ticket board</h2>
        <span className="count">{tickets.length}</span>
      </div>
      <div className="ticket-stack">
        {tickets.map((t, i) => {
          const isResolved = t.state === "resolved" || resolved.has(t.id);
          const isRunning = running === t.id;
          return (
            <article
              key={t.id}
              className={[
                "ticket",
                selected === t.id && "selected",
                isRunning && "running",
                isResolved && "resolved",
              ].filter(Boolean).join(" ")}
              style={{ animationDelay: `${i * 90}ms` }}
              onClick={() => onSelect(t.id)}
            >
              <div className="ticket-top">
                <span className="ticket-icon"><Icon name={TYPE_ICON[t.type] ?? "spark"} /></span>
                <div className="ticket-title">
                  <span className="ticket-id">#{t.id} · {TICKET_TYPES[t.type] ?? t.type}</span>
                  <strong>{t.subject}</strong>
                </div>
                {isResolved && <span className="stamp"><Icon name="check" size={14} /> Resolved</span>}
              </div>
              <p className="ticket-who">{t.requester}</p>
              <p className="ticket-note">{t.notes}</p>
              <div className="ticket-foot">
                <span className={`status s-${t.status}`}>{STATUS_LABEL[t.status] ?? t.status}</span>
                <button
                  className="btn btn-run"
                  disabled={running !== null}
                  onClick={(ev) => { ev.stopPropagation(); onRun(t.id); }}
                >
                  {isRunning ? <><span className="spinner" /> Running…</> : <><Icon name="play" size={14} /> {isResolved ? "Run again" : "Run team"}</>}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
