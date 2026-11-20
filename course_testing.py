"""Shared test helpers for this course. Not a lesson, but worth reading once.

Two jobs:
1. ``load()`` imports a lesson file from either ``solution/`` (default) or ``starter/``.
   Run ``TARGET=starter pytest modules/<module>`` to check your own work.
2. ``FakeLLM`` stands in for ``openai.OpenAI``. It returns scripted replies and records
   every request, so tests run offline with no API key and give the same result every time.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from openai.types import CreateEmbeddingResponse
from openai.types.chat import ChatCompletion

ROOT = Path(__file__).parent


def target() -> str:
    return os.environ.get("TARGET", "solution")


def load(module_dir: str, filename: str):
    """Import modules/<module_dir>/<TARGET>/<filename> under a unique name."""
    path = ROOT / "modules" / module_dir / target() / filename
    name = f"_course_{module_dir.replace('-', '_')}_{target()}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def completion(
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    model: str = "fake-model",
) -> ChatCompletion:
    """Build a real ChatCompletion object, exactly the shape the OpenAI SDK returns.

    tool_calls looks like: [{"name": "add", "arguments": {"a": 1, "b": 2}}]
    """
    message: dict[str, Any] = {"role": "assistant", "content": content}
    finish = "stop"
    if tool_calls:
        finish = "tool_calls"
        message["tool_calls"] = [
            {
                "id": call.get("id", f"call_{i}"),
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["arguments"]
                    if isinstance(call.get("arguments"), str)
                    else json.dumps(call.get("arguments", {})),
                },
            }
            for i, call in enumerate(tool_calls)
        ]
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
    )


def fake_embedding(text: str, dims: int = 64) -> list[float]:
    """A tiny, deterministic bag-of-words embedding. Similar words give similar vectors."""
    vec = [0.0] * dims
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeLLM:
    """Drop-in stand-in for ``OpenAI(...)``.

    Each item in ``replies`` can be a string (plain answer), a ChatCompletion
    (built with ``completion()``), an Exception (raised), or a callable that
    receives the request kwargs and returns one of those.
    """

    def __init__(self, replies: list[Any] | None = None):
        self.replies = list(replies or [])
        self.requests: list[dict[str, Any]] = []
        self.embedding_requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.embeddings = SimpleNamespace(create=self._embed)

    def _create(self, **kwargs: Any) -> ChatCompletion:
        self.requests.append(copy.deepcopy(kwargs))
        if not self.replies:
            raise AssertionError("FakeLLM ran out of scripted replies")
        reply = self.replies.pop(0)
        if callable(reply) and not isinstance(reply, ChatCompletion):
            reply = reply(kwargs)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, str):
            reply = completion(reply)
        return reply

    def _embed(self, *, input: str | list[str], model: str, **kwargs: Any) -> CreateEmbeddingResponse:
        texts = [input] if isinstance(input, str) else list(input)
        self.embedding_requests.append({"input": texts, "model": model})
        return CreateEmbeddingResponse.model_validate(
            {
                "object": "list",
                "model": model,
                "data": [
                    {"object": "embedding", "index": i, "embedding": fake_embedding(t)} for i, t in enumerate(texts)
                ],
                "usage": {"prompt_tokens": 0, "total_tokens": 0},
            }
        )
