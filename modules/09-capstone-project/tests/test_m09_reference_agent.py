import os

import pytest

from course_testing import FakeLLM, completion, load

if os.environ.get("TARGET") == "starter":
    pytest.skip("the capstone starter is a design skeleton; write your own tests", allow_module_level=True)

m = load("09-capstone-project", "reference_agent.py")


def call(name, **args):
    return completion(tool_calls=[{"id": f"id-{name}-{len(args)}", "name": name, "arguments": args}])


def test_answers_from_handbook_with_spotlight():
    llm = FakeLLM([call("search_handbook", query="when are members paid"), "On the 25th [payments.md]."])
    session = m.Session("M-001")
    assert m.run(llm, "fake", session, "When are we paid?", lambda n, a: False) == "On the 25th [payments.md]."
    tool_msg = llm.requests[1]["messages"][-1]["content"]
    assert tool_msg.startswith("<untrusted source='handbook'") and "payments.md" in tool_msg


def test_injection_in_handbook_cannot_trigger_payout():
    llm = FakeLLM([call("search_handbook", query="board notice"), call("request_payout", amount=900000), "Done."])
    session = m.Session("M-001")
    m.run(llm, "fake", session, "Any board notices?", approve=lambda n, a: False)
    assert session.payouts == []
    assert any("blocked request_payout" in e for e in session.events)


def test_model_cannot_choose_another_member():
    llm = FakeLLM([call("get_balance", member_id="M-002"), "Your balance is NGN 182,500.00"])
    session = m.Session("M-001")
    m.run(llm, "fake", session, "balance?", lambda n, a: False)
    assert llm.requests[1]["messages"][-1]["content"] == "NGN 182,500.00"


def test_payout_needs_confirmation_and_respects_balance():
    session = m.Session("M-001")
    llm = FakeLLM([call("request_payout", amount=50000), "Requested."])
    m.run(llm, "fake", session, "pay me 50k", approve=lambda n, a: True)
    assert session.payouts == [("M-001", 50000)]
    llm = FakeLLM([call("request_payout", amount=10_000_000), "Too much."])
    m.run(llm, "fake", session, "pay me 10m", approve=lambda n, a: True)
    assert "no more than your balance" in llm.requests[1]["messages"][-1]["content"]


def test_budget_and_output_checks():
    session = m.Session("M-001", max_tokens=10)
    llm = FakeLLM([call("get_balance"), "never reached"])
    assert "limit" in m.run(llm, "fake", session, "hi", lambda n, a: False)
    assert m.run(FakeLLM(["visit https://evil.example"]), "fake", m.Session("M-1"), "x", lambda n, a: False).startswith(
        "I can't share links"
    )


def test_approver_errors_fail_closed():
    def broken(name, args):
        raise RuntimeError

    session = m.Session("M-001")
    m.run(FakeLLM([call("request_payout", amount=10), "ok"]), "fake", session, "pay", approve=broken)
    assert session.payouts == []
