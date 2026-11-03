"""Boss: reads each ticket, routes it to teammates, and makes the final call."""

from backend.models import BossDecision
from backend.team import make_agent

TOOLS = {
    "get_open_tickets", "get_ticket", "update_ticket_status",
    "check_stock", "get_invoice", "get_lease", "get_cash_balance", "check_discount",
    "list_approval_requests", "list_drafts",
    "get_bills_due", "get_low_stock", "list_store_tasks",
}

boss = make_agent("boss", BossDecision, TOOLS)
