"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

The React dashboard calls these routes on http://localhost:8000. Every shop fact
goes through the campus-customs MCP server (mcp_server/server.py) on
data/campus_customs_new.db. Agents only prepare payments; the approve route is
the only thing that moves cash, and only after a person clicks Approve.

Routes
    GET  /tickets                      the tickets and whether each is open or resolved
    GET  /tickets/{ticket_id}          one ticket with its history, drafts, and requests
    POST /tickets/{ticket_id}/run      run the agent team on one ticket
    GET  /events                       recent agent events (what each agent said, which tools)
    GET  /approvals                    payment / purchase requests waiting for a person
    POST /approvals/{request_id}/approve   a person approves: pays and changes cash
    POST /approvals/{request_id}/reject    a person rejects: no money moves
    GET  /cash                         current checking balance from cash_accounts
    POST /reset                        restore the working database from the original
"""

import asyncio
import json
import os
import re
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# uvicorn is started from backend/, so put the project root on the path for `backend.*` imports.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import audit  # noqa: E402
from backend.run import bills_due_alert, new_run_id, run_ticket  # noqa: E402
from backend.team import MCP_SERVER  # noqa: E402

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = Path(os.environ.get("CAMPUS_DB_PATH", ROOT / "data" / "campus_customs_new.db"))

# One agent run at a time, and no reset while agents are working.
run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with MCP_SERVER:  # one MCP server process for the life of the backend
        yield


app = FastAPI(title="Campus Customs Backend", lifespan=lifespan)
# Only the Vite dashboard page may call these routes from a browser.
DASHBOARD_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=DASHBOARD_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


async def tool(name: str, args: dict[str, Any] | None = None) -> dict:
    """Call one campus-customs MCP tool. A refusal from the tool becomes a 400 with its message."""
    try:
        result = await MCP_SERVER.direct_call_tool(name, args or {})
    except Exception as exc:  # the MCP server's ToolError: not found, refused by a rule, etc.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result if isinstance(result, dict) else json.loads(str(result))


# ---------------------------------------------------------------- tickets


@app.get("/tickets")
async def list_tickets():
    """Every ticket with its status and state ("open" or "resolved")."""
    return await tool("list_tickets")


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    return await tool("get_ticket", {"ticket_id": ticket_id})


@app.post("/tickets/{ticket_id}/run")
async def run_team(ticket_id: int):
    """Run the agent team on one ticket. Boss starts and hands off along the chain.

    Before the ticket, Boss gets the 24-hour bills alert if a bill due within 24 hours
    (or overdue) has no payment request yet. Every step goes to output/audit_trail.json.
    """
    await tool("get_ticket", {"ticket_id": ticket_id})  # 400 if the ticket doesn't exist
    if run_lock.locked():
        raise HTTPException(status_code=409, detail="The team is already working. Try again when it finishes.")
    async with run_lock:
        run_id = new_run_id()
        try:
            alert = await bills_due_alert(run_id)
            decision = await run_ticket(ticket_id, run_id)
        except Exception as exc:  # token/loop limit hit, model error, etc. (already in the audit trail)
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "bills_alert": alert.model_dump() if alert else None,
        "decision": decision.model_dump(),
        "ticket": await tool("get_ticket", {"ticket_id": ticket_id}),
    }


# ---------------------------------------------------------------- agent events


def simplify(row: dict) -> dict:
    """Turn one audit row into what the board shows: who, what they said, which tool."""
    d, event = row["detail"], row["event"]
    out = {k: row.get(k) for k in ("timestamp", "run_id", "ticket_id", "agent", "parent_agent", "depth", "event")}
    if event == "run_start":
        out["said"] = d.get("prompt")
    elif event == "model_response":
        out["said"] = d.get("text") or None
        out["tools"] = d.get("tool_calls", [])
    elif event == "tool_call":
        out["tool"], out["args"] = d.get("tool"), d.get("args")
    elif event == "tool_result":
        out["tool"], out["output"] = d.get("tool"), d.get("output", d.get("error"))
    elif event == "delegation":
        out["to"], out["said"] = d.get("to"), d.get("request")
    elif event == "guardrail":
        out["said"] = d.get("reason") or d.get("delegation_refused") or json.dumps(d)
        out["detail"] = d
    elif event == "run_end":
        report = d.get("output") or {}
        if isinstance(report, str):  # older rows: a long report was cut to text by the audit writer
            m = re.search(r'"summary": "((?:[^"\\]|\\.)*)"', report)
            report = {"summary": m.group(1) if m else report[:300]}
        out["said"] = report.get("summary")
        out["report"] = report
    elif event == "error":
        out["said"] = d.get("message")
    out["usage"] = row.get("usage") or {}
    return out


@app.get("/events")
async def events(
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
    after: str | None = Query(None, description="only events with a timestamp after this one (for refresh)"),
):
    """Recent agent events, newest first: what each agent said and which tools it used."""
    path = audit.AUDIT_PATH
    rows = json.loads(path.read_text()) if path.exists() and path.stat().st_size else []
    shown = [r for r in rows if r["event"] not in ("user_prompt", "model_request")]
    if ticket_id is not None:
        shown = [r for r in shown if r.get("ticket_id") == ticket_id]
    if run_id:
        shown = [r for r in shown if r.get("run_id") == run_id]
    if after:
        shown = [r for r in shown if r["timestamp"] > after]
    latest = shown[-limit:][::-1]
    return {"count": len(latest), "total_events": len(rows), "events": [simplify(r) for r in latest]}


# ---------------------------------------------------------------- approvals (a person, not an agent)


class Approve(BaseModel):
    approved_by: str = Field(min_length=1, description="The person approving, e.g. 'Cedric'.")


class Reject(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.get("/approvals")
async def approvals(status: str = "pending"):
    """Payment and purchase-order requests the agents prepared (pending by default, or 'all')."""
    return await tool("list_approval_requests", {"status": status})


@app.post("/approvals/{request_id}/approve")
async def approve(request_id: int, body: Approve):
    """A person clicked Approve. This is the only route that moves cash.

    The MCP server re-checks everything: the request is pending, the approver is not an
    agent, the vendor/invoice is still valid, and cash won't go negative (if it would,
    the payment is refused and nothing changes).
    """
    if run_lock.locked():
        raise HTTPException(status_code=409, detail="The team is working. Approve when it finishes.")
    result = await tool("approve_and_pay", {"request_id": request_id, "approved_by": body.approved_by})
    return {"result": result, "cash": await tool("get_cash_balance")}


@app.post("/approvals/{request_id}/reject")
async def reject(request_id: int, body: Reject):
    return await tool("reject_request", {"request_id": request_id, "rejected_by": body.rejected_by,
                                         "reason": body.reason})


# ---------------------------------------------------------------- cash and reset


@app.get("/cash")
async def cash():
    """Current checking balance from cash_accounts, plus pending requests."""
    data = await tool("get_cash_balance")
    return {
        "account": data["account"],
        "balance": data["balance"],
        "as_of": data["as_of"],
        "pending_requests_total": data["pending_requests_total"],
        "balance_if_all_pending_paid": data["balance_if_all_pending_paid"],
        "payments_made": data["payments_made"],
    }


@app.post("/reset")
async def reset():
    """Restore data/campus_customs_new.db from the original for a fresh run.

    Clears the board tables too (requests, drafts, store tasks, status history).
    The audit trail is NOT wiped: it is append-only, and runs are told apart by run_id.
    """
    if run_lock.locked():
        raise HTTPException(status_code=409, detail="The team is working. Reset when it finishes.")
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail=f"Original database missing: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return {"reset": True, "database": str(WORKING_DB.relative_to(ROOT)) if WORKING_DB.is_relative_to(ROOT) else str(WORKING_DB),
            "cash": await cash(), "tickets": await list_tickets()}


@app.get("/")
async def root():
    return {"service": "Campus Customs backend", "docs": "/docs",
            "routes": ["/tickets", "/tickets/{id}/run", "/events", "/approvals", "/cash", "/reset"]}
