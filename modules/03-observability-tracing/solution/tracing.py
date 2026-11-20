"""Module 03: OpenTelemetry traces for an agent: one agent span, child spans for model and tool calls."""

import json
import os
import sys
from collections.abc import Callable
from urllib.parse import urlparse

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor, SpanExporter
from opentelemetry.trace import Status, StatusCode, Tracer


def setup_tracing(exporter: SpanExporter, service_name: str = "course-agent") -> Tracer:
    """Create a tracer that sends finished spans to `exporter`. Real apps use BatchSpanProcessor."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer(service_name)


def provider_name(base_url: str) -> str:
    host = urlparse(base_url).netloc
    if "groq" in host:
        return "groq"
    if "openrouter" in host:
        return "openrouter"
    if "openai.com" in host:
        return "openai"
    if host.endswith(":11434"):
        return "ollama"
    return "openai_compatible"


def traced_chat(tracer: Tracer, llm, model: str, messages: list[dict], provider: str, **kwargs):
    """One model call inside a 'chat {model}' span with GenAI attributes. Content is not recorded."""
    with tracer.start_as_current_span(f"chat {model}") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", provider)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("app.request.message_count", len(messages))
        try:
            response = llm.chat.completions.create(model=model, messages=messages, **kwargs)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise
        span.set_attribute("gen_ai.response.model", response.model)
        if response.usage:
            span.set_attribute("gen_ai.usage.input_tokens", response.usage.prompt_tokens)
            span.set_attribute("gen_ai.usage.output_tokens", response.usage.completion_tokens)
        return response


def traced_tool(tracer: Tracer, name: str, func: Callable, arguments: dict) -> str:
    """Run a tool inside an 'execute_tool {name}' span. Errors are recorded and returned as text."""
    with tracer.start_as_current_span(f"execute_tool {name}") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", name)
        try:
            result = str(func(**arguments))
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            return f"error: {type(exc).__name__}: {exc}"
        span.set_attribute("app.tool.result_chars", len(result))
        return result


TOOLS = {"multiply": lambda a, b: a * b}
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers.",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        },
    }
]


def run_agent(tracer: Tracer, llm, model: str, question: str, provider: str = "ollama", max_steps: int = 5) -> str:
    with tracer.start_as_current_span("invoke_agent maths-helper") as root:
        root.set_attribute("gen_ai.operation.name", "invoke_agent")
        root.set_attribute("gen_ai.agent.name", "maths-helper")
        messages: list[dict] = [{"role": "user", "content": question}]
        for step in range(max_steps):
            msg = traced_chat(tracer, llm, model, messages, provider, tools=TOOL_SCHEMAS).choices[0].message
            if not msg.tool_calls:
                root.set_attribute("app.agent.steps", step + 1)
                return msg.content or ""
            messages.append(
                {"role": "assistant", "content": msg.content, "tool_calls": [c.model_dump() for c in msg.tool_calls]}
            )
            for call in msg.tool_calls:
                func = TOOLS.get(call.function.name)
                if func is None:
                    result = f"error: unknown tool {call.function.name}"
                else:
                    result = traced_tool(tracer, call.function.name, func, json.loads(call.function.arguments or "{}"))
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        root.set_status(Status(StatusCode.ERROR, "step limit reached"))
        return "Stopped: step limit."


if __name__ == "__main__":
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    tracer = setup_tracing(ConsoleSpanExporter())
    question = " ".join(sys.argv[1:]) or "What is 12 * 34?"
    print(run_agent(tracer, llm, os.getenv("LLM_MODEL", "llama3.2"), question, provider_name(base_url)))
