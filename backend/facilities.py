"""Facilities: the shop space, the lease, and rent notices."""

from backend.models import AgentReport
from backend.team import make_agent

TOOLS = {"get_ticket", "get_lease", "get_cash_balance", "save_draft", "list_drafts",
         "create_store_task", "list_store_tasks", "list_inventory"}

facilities = make_agent("facilities", AgentReport, TOOLS)
