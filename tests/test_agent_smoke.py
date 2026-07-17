import os
from pathlib import Path

import pytest

from interlock.agent import build_agent, make_local_context, run_agent
from interlock.engine.models import Policy


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") and os.getenv("INTERLOCK_RUN_LIVE_TESTS") == "1"),
    reason="requires API key and explicit live-test opt-in",
)
async def test_agent_completes_a_guarded_read(tmp_path: Path) -> None:
    policy = Policy(
        task="inspect the schema",
        allowed_tools={"inspect"},
        allowed_db_ops=set(),
        allowed_db_tables=set(),
        spend_cap_cents=0,
    )
    context = make_local_context(policy, tmp_path / "sandbox", tmp_path / "events.sqlite")
    agent = build_agent(context)

    result = await run_agent(agent, "Use inspect to check the database schema, then reply briefly.", context)

    assert result
