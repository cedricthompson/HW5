"""Run the team from the command line.

    .venv/bin/python -m backend.run --ticket 101
    .venv/bin/python -m backend.run --all
    .venv/bin/python -m backend.run --daily

Every run starts with the 24-hour bills check: if any bill is due within 24 hours
or is overdue, Boss gets a BILLS DUE ALERT before any other work. Then:
- --ticket / --all: Boss works the ticket(s) and delegates from there.
- --daily: Boss runs the daily operations check (bills, low stock, store upkeep,
  customer replies) across the whole shop.

Every step is appended to output/audit_trail.json.
"""

import argparse
import asyncio
import json
import uuid
from datetime import datetime

from backend.models import BossDecision, TeamDeps
from backend.team import MCP_SERVER, run_agent

BILL_ALERT_DAYS = 1  # "due within 24 hours": the shop date has no clock time, so today or tomorrow


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


async def mcp_call(name: str, args: dict) -> dict:
    """Call a campus-customs MCP tool directly (the runner's own checks, not an agent)."""
    result = await MCP_SERVER.direct_call_tool(name, args)
    return result if isinstance(result, dict) else json.loads(str(result))


async def boss(prompt: str, run_id: str, ticket_id: int | None = None) -> BossDecision:
    deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss")
    return await run_agent("boss", prompt, deps)


def bills_alert_prompt(due: dict) -> str:
    lines = []
    for b in due["bills"]:
        when = (f"OVERDUE by {-b['days_until_due']} day(s)" if b["is_overdue"]
                else f"due in {b['days_until_due']} day(s)")
        req = b["approval_request"]
        lines.append(f"- {b['kind']} {b['ref_id']} to {b['payee']}: ${b['amount']}, due {b['due_date']} ({when}); "
                     f"payment request: {'#' + str(req['id']) + ' ' + req['status'] if req else 'NONE'}")
    return (
        f"BILLS DUE ALERT for {due['date_today']}. These bills are due within 24 hours or overdue "
        f"(from get_bills_due):\n" + "\n".join(lines) +
        f"\nTotal ${due['total_due']}; cash ${due['cash_balance']}; cash covers all: {due['cash_covers_all']}.\n"
        "Make sure no bill is paid late: confirm with get_bills_due, have Accounting file any missing "
        "payment request, and tell the human exactly which request IDs to approve today and in what order. "
        "This is not a ticket: leave ticket_status null."
    )


async def bills_due_alert(run_id: str) -> BossDecision | None:
    """Give Boss a report when a bill is due within 24 hours (or overdue) and has no payment request yet.

    Returns None when nothing is due, or when every due bill already has a request waiting on a
    person (Boss already acted on it, so there's no need to spend tokens on the same alert again).
    """
    due = await mcp_call("get_bills_due", {"within_days": BILL_ALERT_DAYS})
    if not any(b["approval_request"] is None for b in due["bills"]):
        return None
    return await boss(bills_alert_prompt(due), run_id)


async def daily_check(run_id: str) -> BossDecision:
    prompt = (
        "Daily operations check for the whole shop (no ticket). Work through your oversight duties: "
        "bills coming up and no overspending (Accounting), low stock (touch base with Inventory), store "
        "upkeep tasks (Facilities), and replies plus low-stock outreach to customers (Customer Service). "
        "Report what you found for each duty and what is waiting on a person. Leave ticket_status null."
    )
    return await boss(prompt, run_id)


async def run_ticket(ticket_id: int, run_id: str) -> BossDecision:
    prompt = (f"Work ticket {ticket_id} from the board. Read it, route it to the right teammates, "
              "make the final call under the shop rules, set the ticket status, and report.")
    return await boss(prompt, run_id, ticket_id)


def show(title: str, decision: BossDecision) -> None:
    print(f"\n===== {title} =====")
    print(json.dumps(decision.model_dump(), indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", type=int, help="ticket id to work")
    group.add_argument("--all", action="store_true", help="work every open ticket")
    group.add_argument("--daily", action="store_true", help="daily operations check across the shop")
    args = parser.parse_args()

    async with MCP_SERVER:  # one MCP server process for the whole run
        run_id = new_run_id()
        alert = await bills_due_alert(run_id)
        if alert:
            show("BILLS DUE ALERT", alert)
        if args.daily:
            show("DAILY CHECK", await daily_check(run_id))
            return
        ids = [t["id"] for t in (await mcp_call("get_open_tickets", {}))["tickets"]] if args.all else [args.ticket]
        for ticket_id in ids:
            show(f"TICKET {ticket_id}", await run_ticket(ticket_id, run_id))


if __name__ == "__main__":
    asyncio.run(main())
