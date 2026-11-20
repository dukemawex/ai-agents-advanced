import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from course_testing import FakeLLM, load, target

m = load("07-production-deploy", "service.py")
KEY = {"X-API-Key": "k"}


def make(llm=None, ready=lambda: True, rate=30, now=None):
    clock = (lambda: now[0]) if now else None
    kwargs = {"clock": clock} if clock else {}
    settings = m.Settings(service_api_key="k", rate_per_minute=rate)
    return TestClient(m.create_app(settings, llm or FakeLLM(["hello"] * 10), ready, **kwargs))


def test_settings_from_env():
    s = m.Settings.from_env({"SERVICE_API_KEY": "x", "LLM_MODEL": "m", "RATE_PER_MINUTE": "5"})
    assert (s.llm_model, s.rate_per_minute) == ("m", 5)
    with pytest.raises(RuntimeError):
        m.Settings.from_env({})


def test_token_bucket_refills():
    now = [0.0]
    bucket = m.TokenBucket(2, 60, clock=lambda: now[0])
    assert bucket.allow("a")[0] and bucket.allow("a")[0]
    allowed, wait = bucket.allow("a")
    assert not allowed and wait == pytest.approx(30)
    assert bucket.allow("b")[0]  # keys are independent
    now[0] = 30
    assert bucket.allow("a")[0]


def test_health_ready_and_request_id():
    c = make()
    r = c.get("/healthz", headers={"X-Request-ID": "abc"})
    assert r.json() == {"status": "alive"} and r.headers["X-Request-ID"] == "abc"
    assert c.get("/readyz").status_code == 200
    assert len(make().get("/healthz").headers["X-Request-ID"]) == 32


def test_not_ready_when_dependency_fails():
    def broken():
        raise ConnectionError

    assert make(ready=broken).get("/readyz").status_code == 503


def test_chat_auth_rate_limit_and_retry_after():
    now = [0.0]
    c = make(rate=2, now=now)
    assert c.post("/v1/chat", json={"message": "hi"}).status_code == 401
    assert c.post("/v1/chat", json={"message": "hi"}, headers=KEY).json()["reply"] == "hello"
    c.post("/v1/chat", json={"message": "hi"}, headers=KEY)
    limited = c.post("/v1/chat", json={"message": "hi"}, headers=KEY)
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) >= 1


def test_logs_are_json_without_message_content(caplog):
    caplog.set_level(logging.INFO, logger="agent-service")
    make().post("/v1/chat", json={"message": "my PIN is 4321"}, headers=KEY)
    records = [json.loads(r.getMessage()) for r in caplog.records if r.name == "agent-service"]
    assert {r["event"] for r in records} >= {"request", "model_call"}
    assert all("4321" not in json.dumps(r) for r in records)


def test_model_failure_is_503():
    r = make(llm=FakeLLM([RuntimeError("boom")])).post("/v1/chat", json={"message": "hi"}, headers=KEY)
    assert r.status_code == 503 and "boom" not in r.text


def test_dockerfile_follows_basics():
    text = (Path(__file__).parents[1] / target() / "Dockerfile").read_text()
    assert "USER appuser" in text and "HEALTHCHECK" in text
    assert text.index("COPY requirements.txt") < text.index("COPY service.py")
    assert "API_KEY=" not in text  # no secrets baked into the image
