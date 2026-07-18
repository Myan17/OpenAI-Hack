"""OpenAI Agents SDK adapter whose custom handlers are guarded before effects."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents import Agent, FunctionTool, Runner
from agents.tool_context import ToolContext

from interlock.api.eventlog import EventLog
from interlock.engine.models import (
    DbAction,
    EnforcementContext,
    FsWriteAction,
    GitHubAction,
    InspectAction,
    Policy,
    TransferAction,
)
from interlock.interceptor import guarded_call
from interlock.tools.sandbox import Sandbox


@dataclass
class AgentContext:
    policy: Policy
    event_log: EventLog
    sandbox: Sandbox
    enforcement: EnforcementContext


def build_agent(context: AgentContext, model: str = "gpt-5.6") -> Agent[AgentContext]:
    """Build an agent whose every local capability invokes Interlock first."""

    return Agent(
        name="Interlock Demo Agent",
        model=model,
        instructions="Use tools only for the confirmed task. Explain blocked tool results and continue safely.",
        tools=[
            _guarded_tool("db", DbAction, context),
            _guarded_tool("transfer", TransferAction, context),
            _guarded_tool("fs_write", FsWriteAction, context),
            _guarded_tool("inspect", InspectAction, context),
            _guarded_tool("github", GitHubAction, context),
        ],
    )


async def run_agent(agent: Agent[AgentContext], prompt: str, context: AgentContext) -> str:
    """Run a configured agent and return its final text output."""

    result = await Runner.run(agent, prompt, context=context)
    return str(result.final_output)


def _guarded_tool(name: str, action_type: type[Any], context: AgentContext) -> FunctionTool:
    """Create an SDK tool whose pre-effect handler routes through Interlock."""

    async def invoke(_tool_context: ToolContext[Any], arguments: str) -> str:
        action = action_type(args=json.loads(arguments))
        result = await guarded_call(
            action,
            context.policy,
            context.enforcement,
            context.event_log,
            context.sandbox,
        )
        return json.dumps(result, default=str)

    return FunctionTool(
        name=name,
        description=f"Interlock-guarded {name} capability.",
        params_json_schema=action_type.model_fields["args"].annotation.model_json_schema(),
        on_invoke_tool=invoke,
    )


def make_local_context(policy: Policy, root: Path, event_db: Path) -> AgentContext:
    """Create a fully local adapter context for the demo and smoke tests."""

    return AgentContext(policy, EventLog(event_db), Sandbox(root), EnforcementContext())
