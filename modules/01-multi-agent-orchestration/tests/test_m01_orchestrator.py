import json

import pytest

from course_testing import FakeLLM, load

m = load("01-multi-agent-orchestration", "orchestrator.py")

PLAN = json.dumps({"tasks": [{"agent": "researcher", "task": "facts"}, {"agent": "writer", "task": "write it"}]})


def test_happy_path_with_approval():
    llm = FakeLLM([PLAN, "fact A", "draft text", "final answer", json.dumps({"approved": True, "feedback": ""})])
    result = m.orchestrate(llm, "fake", "guide to poultry")
    assert result["final"] == "final answer" and result["approved"]
    assert [e["step"] for e in result["trace"]] == ["plan", "delegate", "delegate", "synthesise", "review"]
    # the writer saw the researcher's output as context
    assert "fact A" in llm.requests[2]["messages"][1]["content"]
    assert llm.requests[0]["response_format"] == {"type": "json_object"}


def test_one_revision_then_stop():
    no = json.dumps({"approved": False, "feedback": "add costs"})
    llm = FakeLLM([PLAN, "facts", "draft", "v1", no, "v2", no])
    result = m.orchestrate(llm, "fake", "goal", max_revisions=1)
    assert result["final"] == "v2" and not result["approved"]
    assert "add costs" in llm.requests[5]["messages"][1]["content"]
    assert len(llm.requests) == 7  # bounded: no third draft


@pytest.mark.parametrize(
    "bad",
    [
        "not json",
        json.dumps({"tasks": []}),
        json.dumps({"tasks": [{"agent": "hacker", "task": "x"}]}),
        json.dumps({"tasks": [{"agent": "writer", "task": ""}]}),
        json.dumps({"tasks": [{"agent": "writer", "task": "x"}] * 9}),
    ],
)
def test_bad_plans_are_rejected(bad):
    with pytest.raises(m.PlanError):
        m.make_plan(FakeLLM([bad]), "fake", "goal", m.DEFAULT_TEAM, max_tasks=4)
