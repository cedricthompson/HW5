"""Inventory: checks stock by SKU and size, spots shortfalls, finds the vendor that can restock."""

from backend.models import AgentReport
from backend.team import make_agent

TOOLS = {"get_ticket", "check_stock", "list_inventory", "list_vendors", "get_invoice", "get_low_stock"}

inventory = make_agent("inventory", AgentReport, TOOLS)
