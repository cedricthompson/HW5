"""The Campus Customs agent team: model, MCP connection, delegation, and the agent loop.

- Every agent uses gpt-6-luna through Portkey. No other model is used.
- Every shop fact comes from the campus-customs MCP server (mcp_server/server.py),
  which works on data/campus_customs_new.db. There is no second tools layer.
- Full connectivity: any agent can hand work to any other agent with ask_teammate.
- Every step of every agent loop is appended to output/audit_trail.json.
"""

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage, UsageLimits

from backend import audit
from backend.models import AGENT_LABELS, AgentName, AgentReport, TeamDeps

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "backend" / "prompts"
load_dotenv(ROOT / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- Token and loop limits (shared by every agent working one ticket) ----
TEAM_LIMITS = UsageLimits(
    request_limit=30,           # model calls across the whole team, per ticket
    tool_calls_limit=60,        # MCP + delegation calls, per ticket
    total_tokens_limit=120_000, # input + output tokens, per ticket
)
MAX_DEPTH = 3                   # Boss -> first owner -> next -> next (e.g. Accounting -> Inventory -> Customer Service)
MODEL_SETTINGS = OpenAIChatModelSettings(
    max_tokens=1_500,                # cap on each model reply
    openai_reasoning_effort="none",  # gpt-6-luna on /chat/completions needs this for function tools
)

# Tools only a person may use (the dashboard). Never given to an agent.
HUMAN_ONLY_TOOLS = {"approve_and_pay", "reject_request", "complete_store_task"}
# Fields the MCP server records as "who did this". Always set to the real agent.
IDENTITY_FIELDS = ("requested_by", "updated_by", "author", "created_by")


def build_model() -> OpenAIChatModel:
    key = os.environ["PORTKEY_API_KEY"]
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
    )
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


async def stamp_identity(ctx: RunContext[TeamDeps], call_tool, name: str, tool_args: dict[str, Any]):
    """Runs before every MCP tool call: blocks human-only tools and fills in who is acting."""
    if name in HUMAN_ONLY_TOOLS:
        audit.record(ctx.deps, -1, "guardrail", {"blocked_tool": name, "reason": "human only"})
        return {"error": f"{name} can only be used by a person on the dashboard."}
    label = AGENT_LABELS[ctx.deps.agent]
    for field in IDENTITY_FIELDS:
        if field in tool_args and tool_args[field] != label:
            audit.record(ctx.deps, -1, "guardrail",
                         {"tool": name, "field": field, "given": tool_args[field], "set_to": label})
            tool_args[field] = label
    return await call_tool(name, tool_args)


# One MCP server process, shared by the whole team for a run.
MCP_SERVER = MCPToolset(
    StdioTransport(
        sys.executable,
        [str(ROOT / "mcp_server" / "server.py")],
        env={k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "CAMPUS_DB_PATH")},
        cwd=str(ROOT),
    ),
    id="campus-customs",
    # A refused tool call (e.g. "vendor will not ship") goes back to the model as a failed result
    # it can read and report, instead of a retry loop.
    tool_error_behavior="failed",
    process_tool_call=stamp_identity,
)

TEAM_NOTE = """

---

## Your team (full connectivity)

You can hand work to any teammate with the `ask_teammate` tool: boss, inventory, accounting,
facilities, customer_service. Work as a chain: do your part, then hand off to the next person who
must act (see "Hand off, don't bounce back" in your prompt). Don't send work to everyone. Give them a specific, self-contained request (ticket ID, SKU and
size, invoice or lease ID, and the exact question). They answer with a structured report.

Limits: you cannot ask yourself, you cannot ask someone who is already waiting on you in this
chain, delegation is at most {max_depth} levels deep, and the team has a small number of
delegations per ticket. The team also shares a token budget, so be brief: call each tool once
for the facts you need, and do not repeat calls whose answers you already have.

You are running as **{label}**. Always use that name in any "requested_by", "updated_by",
"author", or "created_by" field.
"""

_agents: dict[str, Agent] = {}


def make_agent(name: AgentName, output_type: type[AgentReport], allowed_tools: set[str]) -> Agent:
    """Build one team member: its prompt file, its MCP tools, and the ask_teammate tool."""
    leaked = allowed_tools & HUMAN_ONLY_TOOLS
    if leaked:
        raise ValueError(f"{name} must not get human-only tools: {leaked}")
    instructions = (PROMPTS / f"{name}.md").read_text() + TEAM_NOTE.format(
        max_depth=MAX_DEPTH, label=AGENT_LABELS[name])
    toolset = MCP_SERVER.filtered(lambda ctx, tool_def: tool_def.name in allowed_tools)
    agent = Agent(
        build_model(),
        name=name,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=instructions,
        toolsets=[toolset],
        model_settings=MODEL_SETTINGS,
        retries=2,
    )
    agent.tool(ask_teammate)
    _agents[name] = agent
    return agent


def get_agent(name: str) -> Agent:
    if name not in _agents:
        importlib.import_module(f"backend.{name}")  # each agent file registers itself
    return _agents[name]


async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, request: str) -> str:
    """Hand part of the work to another agent and get its report back.

    Args:
        teammate: who to ask: boss, inventory, accounting, facilities, or customer_service.
        request: a specific, self-contained request that names the ticket and the exact question.
    """
    deps = ctx.deps
    refusal = None
    if teammate == deps.agent:
        refusal = "You cannot delegate to yourself."
    elif teammate in deps.chain:
        refusal = f"{AGENT_LABELS[teammate]} is already waiting on you in this chain. Answer with what you have."
    elif deps.depth >= MAX_DEPTH:
        refusal = f"Delegation is limited to {MAX_DEPTH} levels. Finish this yourself with your own tools."
    elif deps.budget.delegations_used >= deps.budget.max_delegations:
        refusal = "The team has used all its delegations for this ticket. Finish with what you have."
    if refusal:
        audit.record(deps, -1, "guardrail", {"delegation_refused": teammate, "request": request, "reason": refusal})
        return refusal

    deps.budget.delegations_used += 1
    audit.record(deps, -1, "delegation", {"to": teammate, "request": request,
                                          "delegations_used": deps.budget.delegations_used})
    child = TeamDeps(
        run_id=deps.run_id, ticket_id=deps.ticket_id, agent=teammate, parent_agent=deps.agent,
        depth=deps.depth + 1, chain=[*deps.chain, deps.agent], budget=deps.budget,
    )
    report = await run_agent(teammate, request, child, usage=ctx.usage)
    return report.model_dump_json()


def _usage_dict(usage: RunUsage) -> dict[str, int]:
    return {"requests": usage.requests, "tool_calls": usage.tool_calls,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "total_tokens": usage.input_tokens + usage.output_tokens}


def _content(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage | None = None) -> AgentReport:
    """The agent loop. Steps through the model/tool cycle and audits every step."""
    agent = get_agent(name)
    audit.record(deps, 0, "run_start", {"prompt": prompt, "model": MODEL_NAME,
                                        "chain": deps.chain, "limits": {
                                            "request_limit": TEAM_LIMITS.request_limit,
                                            "tool_calls_limit": TEAM_LIMITS.tool_calls_limit,
                                            "total_tokens_limit": TEAM_LIMITS.total_tokens_limit,
                                            "max_tokens_per_reply": MODEL_SETTINGS["max_tokens"]}})
    step = 0
    try:
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=TEAM_LIMITS) as run:
            async for node in run:
                step += 1
                used = _usage_dict(run.usage)
                if Agent.is_user_prompt_node(node):
                    audit.record(deps, step, "user_prompt", {"prompt": node.user_prompt}, used)
                elif Agent.is_model_request_node(node):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            audit.record(deps, step, "tool_result", {
                                "tool": part.tool_name, "tool_call_id": part.tool_call_id,
                                "output": _content(part.content)}, used)
                        elif isinstance(part, RetryPromptPart):
                            audit.record(deps, step, "tool_result", {
                                "tool": part.tool_name, "tool_call_id": part.tool_call_id,
                                "error": str(part.content)}, used)
                    audit.record(deps, step, "model_request", {
                        "parts": [p.part_kind for p in node.request.parts]}, used)
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    calls = [p for p in resp.parts if isinstance(p, ToolCallPart)]
                    audit.record(deps, step, "model_response", {
                        "model": resp.model_name,
                        "text": " ".join(p.content for p in resp.parts if isinstance(p, TextPart)),
                        "tool_calls": [c.tool_name for c in calls],
                        "reply_tokens": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
                    }, used)
                    for c in calls:
                        audit.record(deps, step, "tool_call", {
                            "tool": c.tool_name, "tool_call_id": c.tool_call_id, "args": c.args_as_dict()}, used)
                elif Agent.is_end_node(node):
                    pass
        output: AgentReport = run.result.output
    except Exception as exc:
        audit.record(deps, step, "error", {"type": type(exc).__name__, "message": str(exc)})
        raise
    audit.record(deps, step + 1, "run_end", {"output": output.model_dump()}, _usage_dict(run.usage))
    return output
