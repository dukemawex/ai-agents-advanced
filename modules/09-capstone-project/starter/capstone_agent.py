"""Capstone starter: a skeleton with the shape the rubric expects. Replace every TODO with your design.

Suggested layout once it grows: agent.py, tools/, retrieval/, guardrails.py, telemetry.py,
budget.py, service.py, evals/, tests/, Dockerfile, .github/workflows/ci.yml
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Session:
    user_id: str  # comes from your login system, never from the model
    max_tokens: int = 20_000
    tokens_used: int = 0
    tainted: bool = False
    events: list[str] = field(default_factory=list)


# TODO: define your tools. At least one reads untrusted content; at least one is high risk.
TOOL_SCHEMAS: list[dict] = []
TOOLS: dict[str, Callable] = {}
HIGH_RISK: set[str] = set()

SYSTEM = "TODO: write a clear system prompt: role, task, rules, output format, and spotlighting rules."


def run(llm, model: str, session: Session, user_message: str, approve: Callable[[str, dict], bool]) -> str:
    """The agent loop. Build it up module by module:

    - step limit and token budget (advanced 06)
    - tool registry and argument validation (intermediate 01, advanced 08)
    - retrieval with citations (intermediate 03)
    - taint tracking, tool gating with fail-closed approval, output checks (advanced 05)
    - tracing spans for agent, model and tool calls (advanced 03)
    - retries with backoff and fallback (intermediate 07)
    """
    raise NotImplementedError("Design and build your capstone agent here")
