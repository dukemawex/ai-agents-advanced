"""Module 06 starter: measure and cut cost and latency: cache, routing, cascade, trimming, budgets."""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field

# Example prices in USD per million tokens. Keep real prices in config and check your provider's page.
PRICES = {"small-model": (0.05, 0.08), "large-model": (0.59, 0.79)}


def estimate_tokens(text: str) -> int:
    """Rough rule of thumb: about 4 characters per token for English."""
    return max(1, len(text) // 4)


def cost_usd(model: str, input_tokens: int, output_tokens: int, prices: dict = PRICES) -> float:
    price_in, price_out = prices[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class ResponseCache:
    """In-memory cache keyed by a hash of (model, messages), with a time-to-live."""

    def __init__(self, ttl_seconds: float = 3600, clock: Callable[[], float] = time.monotonic):
        self.ttl, self.clock = ttl_seconds, clock
        self.store: dict[str, tuple[float, str]] = {}
        self.hits = self.misses = 0

    @staticmethod
    def key(model: str, messages: list[dict]) -> str:
        return hashlib.sha256(json.dumps([model, messages], sort_keys=True).encode()).hexdigest()

    def get(self, model: str, messages: list[dict]) -> str | None:
        # TODO: look up self.key(...). If found and younger than self.ttl (use self.clock()),
        # count a hit and return the value. Otherwise count a miss and return None.
        raise NotImplementedError

    def put(self, model: str, messages: list[dict], value: str) -> None:
        # TODO: store (self.clock(), value) under self.key(...).
        raise NotImplementedError


def trim_context(messages: list[dict], max_tokens: int) -> list[dict]:
    """Keep the system message and the newest messages that fit in max_tokens (estimated)."""
    # TODO 1: always keep messages[0] (the system message) and count its tokens.
    # TODO 2: walk the rest from newest to oldest, keeping messages while they fit.
    #         Always keep at least the newest message, even if it alone is over budget.
    # TODO 3: return system + kept messages in their original order.
    raise NotImplementedError


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    max_usd: float
    spent_usd: float = 0.0
    calls: list[dict] = field(default_factory=list)

    def charge(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record a call's cost. Raise BudgetExceeded once spending passes max_usd."""
        # TODO: compute cost_usd, add it to spent_usd, append a record to calls,
        # raise BudgetExceeded if spent_usd > max_usd, else return the cost.
        raise NotImplementedError


HARD_WORDS = ("explain why", "compare", "step by step", "analyse", "analyze", "plan", "prove", "code")


def route_model(question: str, small: str = "small-model", large: str = "large-model") -> str:
    """A cheap heuristic router: long or 'hard' questions go to the large model."""
    q = question.lower()
    return large if len(q) > 400 or any(w in q for w in HARD_WORDS) else small


class OptimizedClient:
    """Wraps an OpenAI-compatible client with caching, budget tracking and a cheap-first cascade."""

    def __init__(self, llm, cache: ResponseCache, budget: Budget):
        self.llm, self.cache, self.budget = llm, cache, budget

    def chat(self, model: str, messages: list[dict]) -> str:
        cached = self.cache.get(model, messages)
        if cached is not None:
            return cached
        response = self.llm.chat.completions.create(model=model, messages=messages, temperature=0)
        usage = response.usage
        self.budget.charge(model, usage.prompt_tokens, usage.completion_tokens)
        text = response.choices[0].message.content or ""
        self.cache.put(model, messages, text)
        return text

    def cascade(self, messages: list[dict], good_enough: Callable[[str], bool], small: str, large: str) -> tuple:
        first = self.chat(small, messages)
        if good_enough(first):
            return first, small
        return self.chat(large, messages), large


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from course_testing import FakeLLM, completion

    llm = FakeLLM(
        [
            completion("Paid on the 25th.", prompt_tokens=40, completion_tokens=6),
            completion("I am not sure.", prompt_tokens=40, completion_tokens=5),
            completion("A detailed, correct comparison...", prompt_tokens=40, completion_tokens=300),
            completion("x", prompt_tokens=2_000_000, completion_tokens=0),
        ]
    )
    client = OptimizedClient(llm, ResponseCache(), Budget(max_usd=0.10))
    q = [{"role": "user", "content": "When are members paid?"}]
    print("1st:", client.chat("small-model", q), "| 2nd (cache):", client.chat("small-model", q))
    print("cache hits/misses:", client.cache.hits, client.cache.misses)
    print("router:", route_model("When are members paid?"), "/", route_model("Compare drip and sprinkler irrigation"))
    hard = [{"role": "user", "content": "Compare drip and sprinkler irrigation"}]
    print("cascade:", client.cascade(hard, lambda t: "not sure" not in t, "small-model", "large-model"))
    try:
        client.chat("large-model", [{"role": "user", "content": "huge prompt"}])
    except BudgetExceeded as err:
        print("budget stop:", err)
    print(f"spent so far: ${client.budget.spent_usd:.6f}")
