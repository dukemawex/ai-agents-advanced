import pytest

from course_testing import FakeLLM, completion, load

m = load("06-cost-latency-optimization", "optimize.py")


def test_cost_math():
    assert m.cost_usd("large-model", 1_000_000, 1_000_000) == pytest.approx(0.59 + 0.79)
    assert m.estimate_tokens("abcd" * 10) == 10


def test_cache_hits_and_expires():
    now = [0.0]
    cache = m.ResponseCache(ttl_seconds=10, clock=lambda: now[0])
    msgs = [{"role": "user", "content": "hi"}]
    assert cache.get("a", msgs) is None
    cache.put("a", msgs, "hello")
    assert cache.get("a", msgs) == "hello"
    assert cache.get("b", msgs) is None  # different model, different key
    now[0] = 11
    assert cache.get("a", msgs) is None
    assert (cache.hits, cache.misses) == (1, 3)


def test_trim_keeps_system_and_newest():
    msgs = [{"role": "system", "content": "s" * 40}] + [{"role": "user", "content": f"{i}" * 400} for i in range(5)]
    trimmed = m.trim_context(msgs, max_tokens=250)
    assert trimmed[0] == msgs[0]
    assert trimmed[1:] == msgs[-2:]
    huge = [msgs[0], {"role": "user", "content": "x" * 10_000}]
    assert m.trim_context(huge, max_tokens=50) == huge


def test_budget_stops_spending():
    budget = m.Budget(max_usd=0.001)
    budget.charge("small-model", 1000, 1000)
    with pytest.raises(m.BudgetExceeded):
        budget.charge("large-model", 1_000_000, 0)
    assert len(budget.calls) == 2


def test_router():
    assert m.route_model("When are members paid?") == "small-model"
    assert m.route_model("Explain why my yields dropped") == "large-model"
    assert m.route_model("x" * 500) == "large-model"


def test_client_cache_avoids_second_call_and_cascade_escalates():
    llm = FakeLLM(["answer", "not sure", "great answer"])
    client = m.OptimizedClient(llm, m.ResponseCache(), m.Budget(max_usd=1))
    q = [{"role": "user", "content": "q"}]
    assert client.chat("small-model", q) == client.chat("small-model", q) == "answer"
    assert len(llm.requests) == 1
    hard = [{"role": "user", "content": "hard"}]
    assert client.cascade(hard, lambda t: "not sure" not in t, "small-model", "large-model") == (
        "great answer",
        "large-model",
    )
    assert [c["model"] for c in client.budget.calls] == ["small-model", "small-model", "large-model"]


def test_budget_error_propagates_from_client():
    llm = FakeLLM([completion("x", prompt_tokens=10_000_000)])
    with pytest.raises(m.BudgetExceeded):
        m.OptimizedClient(llm, m.ResponseCache(), m.Budget(max_usd=0.01)).chat("large-model", [])
