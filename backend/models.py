"""Data types for the Campus Customs agent team."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

AGENT_LABELS: dict[str, str] = {
    "boss": "Boss",
    "inventory": "Inventory",
    "accounting": "Accounting",
    "facilities": "Facilities",
    "customer_service": "Customer Service",
}

TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "waiting_on_vendor", "resolved", "declined"]


class Fact(BaseModel):
    """One fact an agent relied on, with the MCP tool it came from."""

    fact: str = Field(description="The fact, with its exact value, e.g. 'CC-TEE-WHITE size S has 0 on hand'.")
    source_tool: str = Field(description="The MCP tool that returned it, e.g. 'check_stock'.")


class AgentReport(BaseModel):
    """What every specialist agent returns when it finishes a piece of work."""

    agent: AgentName
    ticket_id: int | None = Field(description="The ticket this work is for, or null if none.")
    summary: str = Field(description="2-4 sentences: what was asked and what was found or done.")
    facts: list[Fact] = Field(default_factory=list, description="Facts used, each from a tool result in this run.")
    actions_taken: list[str] = Field(default_factory=list, description="Requests filed, drafts saved, statuses set.")
    approval_request_ids: list[int] = Field(default_factory=list, description="Approval requests filed (nothing paid).")
    draft_ids: list[int] = Field(default_factory=list, description="Drafts saved on the board (nothing sent).")
    blockers: list[str] = Field(default_factory=list, description="What stops the ticket from moving, and why.")
    recommendation: str = Field(description="One line: what should happen next.")


class BossDecision(AgentReport):
    """Boss's final call on a ticket."""

    agent: Literal["boss"] = "boss"
    final_call: str = Field(description="The decision in 1-3 sentences, e.g. the approved price or payment order.")
    ticket_status: TicketStatus | None = Field(
        description="The status Boss set with update_ticket_status, or null for a daily check with no ticket.")
    human_next_step: str = Field(description="What the person on the dashboard needs to do next, if anything.")


class AuditEvent(BaseModel):
    """One row in output/audit_trail.json. Written for every step of every agent loop."""

    timestamp: str
    run_id: str
    ticket_id: int | None
    agent: str
    parent_agent: str | None
    depth: int
    step: int
    event: Literal[
        "run_start", "user_prompt", "model_request", "model_response",
        "tool_call", "tool_result", "delegation", "guardrail", "run_end", "error",
    ]
    detail: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, int] = Field(default_factory=dict, description="Team-wide token usage so far.")


@dataclass
class TeamBudget:
    """Shared limits for one ticket run, across every agent and delegation."""

    max_delegations: int = 6
    delegations_used: int = 0


@dataclass
class TeamDeps:
    """Passed to every agent run. Says who is running, for which ticket, and how deep."""

    run_id: str
    ticket_id: int | None
    agent: AgentName
    parent_agent: str | None = None
    depth: int = 0
    chain: list[str] = field(default_factory=list)
    budget: TeamBudget = field(default_factory=TeamBudget)
