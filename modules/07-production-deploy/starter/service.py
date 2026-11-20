"""Module 07 starter: a production-shaped agent service: env config, health/readiness, request ids,
JSON logs, per-key rate limits, timeouts and clean errors.

Run:  uvicorn --factory service:create_app --port 8000
"""

import json
import logging
import os
import secrets
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

log = logging.getLogger("agent-service")


@dataclass(frozen=True)
class Settings:
    service_api_key: str
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2"
    rate_per_minute: int = 30
    request_timeout_s: float = 30.0
    max_output_tokens: int = 512

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Settings":
        env = os.environ if env is None else env
        if not env.get("SERVICE_API_KEY"):
            raise RuntimeError("SERVICE_API_KEY must be set")
        return cls(
            service_api_key=env["SERVICE_API_KEY"],
            llm_base_url=env.get("LLM_BASE_URL", cls.llm_base_url),
            llm_api_key=env.get("LLM_API_KEY", cls.llm_api_key),
            llm_model=env.get("LLM_MODEL", cls.llm_model),
            rate_per_minute=int(env.get("RATE_PER_MINUTE", cls.rate_per_minute)),
            request_timeout_s=float(env.get("REQUEST_TIMEOUT_S", cls.request_timeout_s)),
            max_output_tokens=int(env.get("MAX_OUTPUT_TOKENS", cls.max_output_tokens)),
        )


class TokenBucket:
    """Each key gets `capacity` requests that refill continuously over `per_seconds`."""

    def __init__(self, capacity: int, per_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.capacity, self.rate, self.clock = capacity, capacity / per_seconds, clock
        self.buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_time)

    def allow(self, key: str) -> tuple[bool, float]:
        """Return (allowed, seconds to wait before retrying)."""
        # TODO 1: get (tokens, last) for the key; a new key starts full: (capacity, now).
        # TODO 2: refill: tokens = min(capacity, tokens + (now - last) * self.rate)
        # TODO 3: if tokens >= 1, take one, save (tokens - 1, now), return (True, 0.0).
        # TODO 4: otherwise save (tokens, now) and return (False, (1 - tokens) / self.rate).
        raise NotImplementedError


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatOut(BaseModel):
    reply: str
    request_id: str


def json_log(**fields) -> None:
    log.info(json.dumps(fields, default=str))


def create_app(
    settings: Settings | None = None,
    llm=None,
    ready_check: Callable[[], bool] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    settings = settings or Settings.from_env()
    if llm is None:
        from openai import OpenAI

        llm = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.request_timeout_s,
            max_retries=1,
        )
    if ready_check is None:

        def ready_check() -> bool:
            llm.models.list()
            return True

    limiter = TokenBucket(settings.rate_per_minute, 60.0, clock)
    app = FastAPI(title="Dukers Ltd course agent service", version="1.0.0")
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        # TODO 1: reuse the caller's x-request-id header or make one with uuid.uuid4().hex,
        #         and store it on request.state.request_id.
        # TODO 2: time the request, call `await call_next(request)`, set the X-Request-ID response header.
        # TODO 3: json_log(event="request", request_id, method, path, status, latency_ms). No message text!
        # TODO 4: return the response.
        raise NotImplementedError

    def auth_and_limit(x_api_key: Annotated[str | None, Header()] = None) -> str:
        if not x_api_key or not secrets.compare_digest(x_api_key, settings.service_api_key):
            raise HTTPException(401, "missing or wrong X-API-Key")
        allowed, wait = limiter.allow(x_api_key)
        if not allowed:
            raise HTTPException(429, "rate limit exceeded", headers={"Retry-After": str(max(1, round(wait)))})
        return x_api_key

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "alive"}

    @app.get("/readyz")
    def readyz(response: Response) -> dict:
        try:
            ok = bool(ready_check())
        except Exception:
            ok = False
        if not ok:
            response.status_code = 503
        return {"status": "ready" if ok else "not ready"}

    @app.post("/v1/chat", response_model=ChatOut, dependencies=[Depends(auth_and_limit)])
    def chat(body: ChatIn, request: Request) -> ChatOut:
        try:
            completion = llm.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for Kola Farms Cooperative."},
                    {"role": "user", "content": body.message},
                ],
                max_tokens=settings.max_output_tokens,
            )
        except Exception as exc:
            json_log(event="model_error", request_id=request.state.request_id, error=type(exc).__name__)
            raise HTTPException(503, "the model is unavailable, please try again") from exc
        usage = completion.usage
        json_log(
            event="model_call",
            request_id=request.state.request_id,
            model=settings.llm_model,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
        return ChatOut(reply=completion.choices[0].message.content or "", request_id=request.state.request_id)

    return app
