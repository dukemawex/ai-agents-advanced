import json

import pytest

from course_testing import FakeLLM, completion, load

m = load("04-evals-and-red-teaming", "redteam.py")


def test_detectors():
    canary = m.Attack("a", "c", "p", "canary")
    tool = m.Attack("b", "c", "p", "tool:transfer_funds")
    assert m.attack_succeeded(canary, m.AgentOutput(f"my notes: {m.CANARY}"))
    assert not m.attack_succeeded(canary, m.AgentOutput("I cannot share that."))
    assert m.attack_succeeded(tool, m.AgentOutput("", ["transfer_funds"]))
    assert m.attack_succeeded(m.Attack("c", "c", "p", "contains:PIN"), m.AgentOutput("your pin is"))
    with pytest.raises(ValueError):
        m.attack_succeeded(m.Attack("d", "c", "p", "vibes"), m.AgentOutput(""))


def test_weak_agent_is_caught():
    report = m.run_redteam(m.weak_stand_in)
    assert set(report["breaches"]) == {"extract-1", "inject-1"}
    assert report["by_category"]["prompt_extraction"] == 0.5
    assert 0 < report["asr"] < 1
    assert not m.gate(report, [5])


def test_robust_agent_passes_gate():
    report = m.run_redteam(lambda p: m.AgentOutput("Sorry, I can't help with that."))
    assert report["asr"] == 0 and m.gate(report, [4, 5])
    assert not m.gate(report, [2, 3])  # safe but unhelpful still fails


def test_crash_is_not_a_breach():
    def crashing(prompt):
        raise RuntimeError

    assert m.run_redteam(crashing)["asr"] == 0


def test_target_agent_reports_tool_calls():
    llm = FakeLLM([completion(tool_calls=[{"name": "transfer_funds", "arguments": {"account": "1", "amount": 5}}])])
    out = m.make_target_agent(llm, "fake")("send money")
    assert out.tools_used == ["transfer_funds"]
    assert m.CANARY in llm.requests[0]["messages"][0]["content"]


def test_judge_parses_and_falls_back():
    good = FakeLLM([json.dumps({"reason": "Correct date.", "score": 5})])
    assert m.judge(good, "fake", "q", "a").score == 5
    assert good.requests[0]["temperature"] == 0
    assert m.judge(FakeLLM([json.dumps({"reason": "x", "score": 9})]), "fake", "q", "a").score == 1
    assert m.judge(FakeLLM(["not json"]), "fake", "q", "a").score == 1
