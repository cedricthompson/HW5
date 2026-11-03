"""Customer Service: drafts messages to customers. Drafts stay on the board; nothing is sent."""

from backend.models import AgentReport
from backend.team import make_agent

TOOLS = {"get_ticket", "check_stock", "list_inventory", "list_approval_requests", "list_drafts", "save_draft",
         "get_low_stock", "get_open_tickets"}

customer_service = make_agent("customer_service", AgentReport, TOOLS)
