import { agentName, describe } from "../agents";
import type { AgentEvent } from "../types";
import { Icon } from "./Icon";

const KIND_ICON: Record<string, string> = {
  start: "play", said: "chat", tool: "tool", result: "arrow", handoff: "arrow",
  guard: "shield", done: "check", error: "alert",
};

export function ActivityFeed({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const rows = events
    .map((e) => ({ e, d: describe(e) }))
    .filter((r): r is { e: AgentEvent; d: NonNullable<ReturnType<typeof describe>> } => r.d !== null)
    .reverse(); // newest on top

  const tokens = events.reduce((max, e) => Math.max(max, e.usage?.total_tokens ?? 0), 0);

  return (
    <section className="panel feed">
      <div className="panel-head">
        <h2>Live activity</h2>
        <span className="muted small">{rows.length} steps{tokens ? ` · ${tokens.toLocaleString()} tokens` : ""}</span>
      </div>
      {rows.length === 0 ? (
        <div className="feed-empty">
          {running ? <><span className="spinner dark" /> Waiting for the first step…</> : "Pick a ticket and press Run team. Every step each agent takes shows up here as it happens."}
        </div>
      ) : (
        <ol className="feed-list">
          {rows.map(({ e, d }, i) => (
            <li key={`${e.timestamp}-${e.agent}-${e.event}-${e.tool ?? ""}-${i}`} className={`feed-item k-${d.kind}`} style={{ marginLeft: e.depth * 14 }}>
              <span className={`feed-badge a-${e.agent}`}>{agentName(e.agent)}</span>
              <span className="feed-icon"><Icon name={KIND_ICON[d.kind] ?? "spark"} size={14} /></span>
              <div className="feed-text">
                <span className="feed-main">{d.kind === "tool" ? <code>{d.text}</code> : d.text}</span>
                {d.sub && <span className="feed-sub">{d.sub}</span>}
              </div>
              <time>{e.timestamp.slice(11, 19)}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
