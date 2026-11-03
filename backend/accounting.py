"""Accounting: watches cash and invoices, checks margins, prepares payments and purchase orders for human approval."""

from backend.models import AgentReport
from backend.team import make_agent

TOOLS = {
    "get_ticket", "get_invoice", "get_cash_balance", "check_discount", "check_stock",
    "list_vendors", "get_lease", "list_approval_requests",
    "request_invoice_payment", "request_rent_payment", "request_purchase_order",
    "get_bills_due",
}

accounting = make_agent("accounting", AgentReport, TOOLS)
