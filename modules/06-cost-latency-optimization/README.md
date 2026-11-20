# Module 06: Cost and latency optimisation

**Time:** about 90 minutes.

## Objectives

- Measure cost and latency per request before trying to improve them.
- Cut cost with caching, model routing, a cheap-first cascade and context trimming.
- Enforce a hard budget so a runaway agent cannot spend without limit.
- Know the provider features that help: streaming, prompt caching and batch APIs.

## Concepts in plain English

Agents make many model calls per task, so small waste multiplies. Always **measure first**: log tokens in and out, latency, and cost per request (Module 03 tracing gives you this). Then pick the cheapest fix that works.

| Technique | What it does | Watch out for |
| --- | --- | --- |
| **Response cache** | Same model plus same messages returns the saved answer | Only for deterministic, non-personal requests; set an expiry |
| **Model routing** | Easy requests go to a small, cheap model; hard ones to a big model | The router must be cheap itself; check quality with evals |
| **Cascade** | Try the small model first; escalate only if a check fails | Needs a reliable "good enough" check |
| **Context trimming** | Drop or summarise old messages to stay under a token budget | Never drop the system message or the latest question |
| **Budgets** | Stop when a session exceeds N tokens or N dollars | Fail with a clear message, not a crash |
| **Streaming** | Show tokens as they arrive | Same cost, but feels much faster |
| **Prompt caching** (provider side) | Repeated long prefixes cost less and return faster | Put stable content (system prompt, tools) first |
| **Batch APIs** | Cheaper for jobs that can wait hours | Not for live chat |

Prices and features change often and differ by provider, so keep prices in config, not in code, and check your provider's pricing page.

A quick way to estimate tokens without a tokenizer: about 4 characters per token for English. It is rough (other languages often use more tokens per word), so use the provider's reported `usage` for real accounting.

## Step by step

1. Run the demo. It shows a cache hit, routing, a cascade escalation and a budget stop:
   ```bash
   python modules/06-cost-latency-optimization/solution/optimize.py
   ```
2. In `starter/optimize.py`, complete `ResponseCache`, `trim_context()` and `Budget.charge()`.
3. Test offline:
   ```bash
   TARGET=starter pytest modules/06-cost-latency-optimization
   ```

## Exercises

1. Add streaming (`stream=True`) to a chat call and print tokens as they arrive. Measure time to first token.
2. Run your intermediate eval set through a small and a large Groq model. Compute cost per correct answer for each.
3. Store the cache in SQLite so it survives restarts, with a TTL.
4. Write a router that uses a tiny model to classify difficulty. Is it worth the extra call?

## Checkpoint quiz

1. What should you do before optimising?
2. When is response caching unsafe?
3. What must context trimming always keep?
4. Why does streaming help even though it costs the same?

<details><summary>Answers</summary>

1. Measure tokens, latency and cost per request so you know where the waste is.
2. When answers depend on the user, the time, or private data, or when randomness is wanted.
3. The system message and the latest user message.
4. Users see output sooner, so it feels faster, and they can stop a bad answer early.
</details>

## Further reading

- OpenAI, [Latency optimization](https://platform.openai.com/docs/guides/latency-optimization) and [Prompt caching](https://platform.openai.com/docs/guides/prompt-caching)
- OpenAI, [Batch API](https://platform.openai.com/docs/guides/batch)
- Groq, [Prompt caching](https://console.groq.com/docs/prompt-caching) and [Batch processing](https://console.groq.com/docs/batch)
- Chen et al., [FrugalGPT: How to Use Large Language Models While Reducing Cost](https://arxiv.org/abs/2305.05176)
- OpenAI, [Streaming API responses](https://platform.openai.com/docs/guides/streaming-responses)
