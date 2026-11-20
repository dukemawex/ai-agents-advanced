import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from course_testing import FakeLLM, completion, load

m = load("03-observability-tracing", "tracing.py")


@pytest.fixture
def setup():
    exporter = InMemorySpanExporter()
    return m.setup_tracing(exporter), exporter


def test_agent_trace_tree(setup):
    tracer, exporter = setup
    llm = FakeLLM(
        [
            completion(tool_calls=[{"name": "multiply", "arguments": {"a": 12, "b": 34}}], prompt_tokens=50),
            completion("408", prompt_tokens=70, completion_tokens=3),
        ]
    )
    assert m.run_agent(tracer, llm, "fake", "12*34?", provider="groq") == "408"
    spans = {s.name: s for s in exporter.get_finished_spans()}
    root = spans["invoke_agent maths-helper"]
    tool = spans["execute_tool multiply"]
    chats = [s for s in exporter.get_finished_spans() if s.name == "chat fake"]
    assert len(chats) == 2
    assert all(s.parent.span_id == root.context.span_id for s in [tool, *chats])
    assert len({s.context.trace_id for s in exporter.get_finished_spans()}) == 1
    assert chats[0].attributes["gen_ai.usage.input_tokens"] == 50
    assert chats[1].attributes["gen_ai.usage.output_tokens"] == 3
    assert chats[0].attributes["gen_ai.provider.name"] == "groq"
    assert tool.attributes["gen_ai.tool.name"] == "multiply"
    assert root.attributes["app.agent.steps"] == 2


def test_tool_error_is_marked(setup):
    tracer, exporter = setup
    out = m.traced_tool(tracer, "divide", lambda a, b: a / b, {"a": 1, "b": 0})
    assert out.startswith("error: ZeroDivisionError")
    span = exporter.get_finished_spans()[0]
    assert span.status.status_code == StatusCode.ERROR
    assert any(e.name == "exception" for e in span.events)


def test_model_error_is_marked_and_raised(setup):
    tracer, exporter = setup
    with pytest.raises(TimeoutError):
        m.traced_chat(tracer, FakeLLM([TimeoutError("slow")]), "fake", [], "ollama")
    assert exporter.get_finished_spans()[0].status.status_code == StatusCode.ERROR


def test_no_prompt_content_in_attributes(setup):
    tracer, exporter = setup
    m.traced_chat(tracer, FakeLLM(["ok"]), "fake", [{"role": "user", "content": "my PIN is 1234"}], "ollama")
    attrs = exporter.get_finished_spans()[0].attributes
    assert all("1234" not in str(v) for v in attrs.values())


def test_provider_name():
    assert m.provider_name("https://api.groq.com/openai/v1") == "groq"
    assert m.provider_name("http://localhost:11434/v1") == "ollama"
    assert m.provider_name("https://example.com/v1") == "openai_compatible"
