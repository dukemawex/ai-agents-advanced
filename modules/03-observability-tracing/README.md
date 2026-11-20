# Module 03: Observability and tracing

**Time:** about 90 minutes. **Uses:** [OpenTelemetry](https://opentelemetry.io/docs/languages/python/) for Python.

## Objectives

- Explain logs, metrics and traces, and why agents need traces most.
- Wrap every model call and tool call in an OpenTelemetry **span**, nested under one agent span.
- Record useful attributes (model, tokens, tool name) using the GenAI semantic conventions.
- Mark failures clearly and keep secrets out of telemetry.

## Concepts in plain English

When a user says "the agent gave a weird answer yesterday", you need to see exactly what happened: which model calls, which tools, what they returned, how long each took, and how many tokens they used. That is **observability**.

- **Logs** are individual lines of text: "tool failed".
- **Metrics** are numbers over time: requests per minute, average cost.
- **Traces** show one request as a tree of timed steps called **spans**. For agents, traces are the most useful, because an agent run *is* a tree: the run contains model calls, which trigger tool calls, which may trigger more model calls.

**OpenTelemetry (OTel)** is the open standard for this. You create spans in your code once, then send them to any backend that accepts the OTLP format: Jaeger, Grafana Tempo, Honeycomb, Langfuse, Arize Phoenix and many more.

OTel has **semantic conventions** for generative AI, so every tool names things the same way. The ones we use:

| Attribute | Example |
| --- | --- |
| `gen_ai.operation.name` | `invoke_agent`, `chat`, `execute_tool` |
| `gen_ai.provider.name` | `openai`, `groq`, `ollama` |
| `gen_ai.request.model` / `gen_ai.response.model` | `llama3.2` |
| `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` | `812` / `64` |
| `gen_ai.tool.name` | `get_weather` |

These GenAI conventions are still marked as in development, so names can change. Check the [current spec](https://github.com/open-telemetry/semantic-conventions-genai) when you upgrade.

**Privacy:** prompts and tool results can contain personal data and secrets. By default, record sizes and counts, not content. If you do record content for debugging, redact it and limit who can see it.

## Step by step

1. Run the agent with console tracing. Each finished span is printed as JSON:
   ```bash
   python modules/03-observability-tracing/solution/tracing.py "What is 12 * 34?"
   ```
   Find the `invoke_agent` span and the `chat` and `execute_tool` spans inside it (same `trace_id`, linked by `parent_id`).
2. In `starter/tracing.py`, complete `traced_chat()` and `traced_tool()`.
3. Test offline with an in-memory exporter:
   ```bash
   TARGET=starter pytest modules/03-observability-tracing
   ```
4. Optional: run [Jaeger](https://www.jaegertracing.io/docs/latest/getting-started/) locally, install `opentelemetry-exporter-otlp`, and send spans to it.

## Exercises

1. Add a `gen_ai.conversation.id` attribute so all turns of one chat can be grouped.
2. Add a metric: a counter of tokens per model, using the OTel metrics API.
3. Make a tool fail and find the error in the trace. What does `record_exception` add?
4. Send traces to Langfuse or Phoenix (both accept OTLP) and compare their views.

## Checkpoint quiz

1. What is the difference between a log line and a trace?
2. Which span is the parent of a tool call span?
3. Why use standard attribute names?
4. Why avoid recording full prompts by default?

<details><summary>Answers</summary>

1. A log line is one event; a trace links all the timed steps of one request into a tree.
2. The agent run span (`invoke_agent`), with the model call spans beside it as siblings.
3. So any backend and any teammate can read your traces without custom mapping.
4. Prompts can contain personal data and secrets, and telemetry is often widely shared and kept for a long time.
</details>

## Further reading

- OpenTelemetry, [Python getting started](https://opentelemetry.io/docs/languages/python/getting-started/)
- OpenTelemetry, [Traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
- OpenTelemetry, [GenAI semantic conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)
- Langfuse, [OpenTelemetry integration](https://langfuse.com/integrations/native/opentelemetry)
- Arize Phoenix, [Tracing](https://arize.com/docs/phoenix/tracing/llm-traces)
