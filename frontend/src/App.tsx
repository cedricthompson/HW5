import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, API_URL } from "./api";
import { liveState, money, reports, handoffs } from "./agents";
import type { AgentEvent, AgentName, ApprovalRequest, Cash, RunResponse, Ticket } from "./types";
import { TicketList } from "./components/TicketList";
import { AgentTeam } from "./components/AgentTeam";
import { ActivityFeed } from "./components/ActivityFeed";
import { RunSummary } from "./components/RunSummary";
import { CashCard } from "./components/CashCard";
import { Approvals } from "./components/Approvals";
import { Icon } from "./components/Icon";

const LS = { runs: "cc.runs", resolved: "cc.resolved", approver: "cc.approver" };
const POLL_MS = 800;

function load<T>(key: string, fallback: T): T {
  try { return JSON.parse(localStorage.getItem(key) ?? "") as T; } catch { return fallback; }
}

type Toast = { text: string; tone: "ok" | "warn" | "err"; id: number };

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [today, setToday] = useState("");
  const [cash, setCash] = useState<Cash | null>(null);
  const [cashFlash, setCashFlash] = useState(0);
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [running, setRunning] = useState<number | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]); // the shown run, oldest first
  const [runs, setRuns] = useState<Record<number, RunResponse>>(() => load(LS.runs, {}));
  const [resolved, setResolved] = useState<Set<number>>(() => new Set(load<number[]>(LS.resolved, [])));
  const [approver, setApprover] = useState(() => localStorage.getItem(LS.approver) ?? "");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const approvalsRef = useRef<HTMLElement>(null);

  useEffect(() => { localStorage.setItem(LS.runs, JSON.stringify(runs)); }, [runs]);
  useEffect(() => { localStorage.setItem(LS.resolved, JSON.stringify([...resolved])); }, [resolved]);
  useEffect(() => { localStorage.setItem(LS.approver, approver); }, [approver]);

  const say = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = Date.now();
    setToast({ text, tone, id });
    setTimeout(() => setToast((t) => (t?.id === id ? null : t)), 5200);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setTickets(t.tickets);
      setToday(t.date_today);
      setCash(c);
      setRequests(a.requests);
      setBackendUp(true);
      setSelected((s) => s ?? t.tickets[0]?.id ?? null);
    } catch {
      setBackendUp(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // When a finished ticket is selected, load that run's events so its story is still on screen.
  useEffect(() => {
    if (selected == null || running != null) return;
    const past = runs[selected];
    if (!past) { setEvents([]); return; }
    api.events({ run_id: past.run_id, limit: 1000 })
      .then((r) => setEvents(r.events.slice().reverse()))
      .catch(() => setEvents([]));
  }, [selected, running, runs]);

  const runTeam = async (id: number) => {
    setSelected(id);
    setRunning(id);
    setEvents([]);
    let after = "";
    try { after = (await api.events({ limit: 1 })).events[0]?.timestamp ?? ""; } catch { /* first run */ }

    let inFlight = false;
    const pull = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const r = await api.events({ after, limit: 1000 });
        setEvents(r.events.slice().reverse());
      } catch { /* keep the last good view */ } finally { inFlight = false; }
    };
    const timer = setInterval(pull, POLL_MS);
    try {
      const res = await api.run(id);
      clearInterval(timer);
      inFlight = false;
      await pull();
      setRuns((r) => ({ ...r, [id]: res }));
      setResolved((s) => new Set(s).add(id));
      say(`Ticket #${id}: the team finished. ${res.decision.final_call ?? ""}`);
    } catch (err) {
      say(`Ticket #${id} run failed: ${(err as Error).message}`, "err");
    } finally {
      clearInterval(timer);
      setRunning(null);
      refresh();
    }
  };

  const approve = async (r: ApprovalRequest) => {
    const before = cash?.balance;
    try {
      const res = await api.approve(r.id, approver.trim());
      setCash(res.cash);
      setCashFlash((f) => f + 1);
      if (res.result.paid) {
        say(`Paid ${money(res.result.amount)} · checking ${money(before)} → ${money(res.result.balance_after)}`);
      } else {
        say(`Refused: ${res.result.note ?? res.result.status}`, "warn");
      }
    } catch (err) {
      say((err as Error).message, "err");
    }
    refresh();
  };

  const reject = async (r: ApprovalRequest) => {
    const reason = window.prompt(`Why are you rejecting request #${r.id}?`);
    if (!reason) return;
    try {
      await api.reject(r.id, approver.trim(), reason);
      say(`Request #${r.id} rejected. No money moved.`, "warn");
    } catch (err) {
      say((err as Error).message, "err");
    }
    refresh();
  };

  const reset = async () => {
    if (!window.confirm("Reset the shop database to the original values for a fresh run?")) return;
    try {
      await api.reset();
      setRuns({});
      setResolved(new Set());
      setEvents([]);
      setCashFlash((f) => f + 1);
      say("Database reset to the original values.");
    } catch (err) {
      say((err as Error).message, "err");
    }
    refresh();
  };

  const live = useMemo(() => liveState(events), [events]);
  const chain = useMemo(() => handoffs(events.filter((e) => e.ticket_id === selected)), [events, selected]);
  const done = useMemo(() => reports(events), [events]);
  const active = useMemo<AgentName | null>(() => {
    if (running == null) return null;
    const last = [...events].reverse().find((e) => live[e.agent]?.phase === "working");
    return last?.agent ?? "boss";
  }, [events, live, running]);

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <div className="crest">CC</div>
          <div>
            <h1>Campus Customs <span>Ops Desk</span></h1>
            <p>Five AI agents run the shop · a person approves every payment</p>
          </div>
        </div>
        <div className="top-right">
          <span className="pill"><Icon name="spark" size={14} /> Shop date {today || "—"}</span>
          <span className={`pill conn ${backendUp ? "up" : backendUp === false ? "down" : ""}`}>
            <i /> {backendUp ? "Backend connected" : backendUp === false ? "Backend offline" : "Connecting…"}
          </span>
          <button className="btn btn-light" onClick={reset} disabled={running !== null}>
            <Icon name="reset" size={14} /> Reset data
          </button>
        </div>
        <div className="stripe" />
      </header>
      {running !== null && <div className="progress"><span /></div>}

      {backendUp === false && (
        <div className="banner">
          <Icon name="alert" /> Can't reach the backend at <code>{API_URL}</code>. Start it from <code>backend/</code> with{" "}
          <code>uvicorn main:app --reload --port 8000</code>, then <button className="link" onClick={refresh}>try again</button>.
        </div>
      )}

      <main className="grid">
        <TicketList
          tickets={tickets}
          selected={selected}
          running={running}
          resolved={resolved}
          onSelect={(id) => running == null && setSelected(id)}
          onRun={runTeam}
        />

        <div className="center">
          <AgentTeam live={live} active={active} chain={chain} running={running !== null} />
          {selected != null && running == null && (
            <RunSummary
              ticketId={selected}
              result={runs[selected] ?? null}
              reports={done}
              pendingCount={requests.length}
              onGoToApprovals={() => approvalsRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
            />
          )}
          <ActivityFeed events={events} running={running !== null} />
        </div>

        <aside className="side">
          <CashCard cash={cash} flash={cashFlash} />
          <Approvals
            ref={approvalsRef}
            requests={requests}
            approver={approver}
            setApprover={setApprover}
            busy={running !== null}
            onApprove={approve}
            onReject={reject}
          />
        </aside>
      </main>

      {toast && (
        <div key={toast.id} className={`toast t-${toast.tone}`}>
          <Icon name={toast.tone === "ok" ? "check" : "alert"} /> {toast.text}
        </div>
      )}
    </div>
  );
}
