import { AGENTS, agentName, type AgentLive } from "../agents";
import type { AgentName } from "../types";
import { Icon } from "./Icon";

interface Props {
  live: Record<AgentName, AgentLive>;
  active: AgentName | null;
  chain: { from: AgentName; to: AgentName }[];
  running: boolean;
}

const PHASE_LABEL = { idle: "Idle", working: "Working", waiting: "Waiting", done: "Done", error: "Error" };

export function AgentTeam({ live, active, chain, running }: Props) {
  // Path of the handoffs in order: Boss → first owner → next …
  const path: AgentName[] = chain.length ? [chain[0].from, ...chain.map((c) => c.to)] : [];

  return (
    <section className="panel team">
      <div className="panel-head">
        <h2>Agent team</h2>
        {running && <span className="live-dot">Live</span>}
      </div>

      <div className="chain">
        {path.length === 0 ? (
          <span className="chain-empty">{running ? "Boss is reading the ticket…" : "Handoffs will appear here when the team runs."}</span>
        ) : (
          path.map((a, i) => (
            <span key={`${a}-${i}`} className="chain-step" style={{ animationDelay: `${i * 120}ms` }}>
              {i > 0 && <span className="chain-arrow" />}
              <span className={`chain-node a-${a}`}>{agentName(a)}</span>
            </span>
          ))
        )}
      </div>

      <div className="agents">
        {AGENTS.map((a) => {
          const s = live[a.id];
          return (
            <article key={a.id} className={`agent a-${a.id} p-${s.phase} ${active === a.id ? "active" : ""}`}>
              <div className="avatar">
                <span>{a.initials}</span>
                {s.phase === "done" && <i className="avatar-check"><Icon name="check" size={12} /></i>}
              </div>
              <div className="agent-body">
                <div className="agent-name">
                  <strong>{a.name}</strong>
                  <span className={`phase ph-${s.phase}`}>
                    {PHASE_LABEL[s.phase]}
                    {s.phase === "working" && <span className="dots"><i /><i /><i /></span>}
                  </span>
                </div>
                <p className="agent-role">{a.role}</p>
                <p className="agent-line" key={s.line}>{s.line}</p>
                {s.tools.length > 0 && (
                  <div className="chips">
                    {s.tools.map((t) => <span key={t} className="chip"><Icon name="tool" size={11} /> {t}</span>)}
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
