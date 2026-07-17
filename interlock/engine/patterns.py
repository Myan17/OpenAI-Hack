"""Stable matching of policy-forbidden patterns against typed actions."""

import json
import re

from interlock.engine.models import ProposedAction


def matches_forbidden(action: ProposedAction, patterns: list[str]) -> str | None:
    """Return the first case-insensitive forbidden pattern matching an action."""

    action_blob = json.dumps(
        action.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    for pattern in patterns:
        if re.search(pattern, action_blob, re.IGNORECASE):
            return pattern
    return None
