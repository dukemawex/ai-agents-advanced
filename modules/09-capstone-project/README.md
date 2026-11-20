# Module 09: Capstone project

**Time:** 2 to 4 weeks, part time. **Builds on:** everything in all three levels.

## The brief

Build and ship a **production-ready agent that does real work for a real (or realistic) organisation**, and prove it is useful, safe and affordable.

The default project is a **cooperative helpdesk agent** for a farming cooperative like the "Kola Farms" examples used throughout the course: members ask about policies, check their balance, and request payouts. You may choose your own domain instead (a school, clinic, shop, NGO or your own startup), as long as it meets every requirement below.

`solution/reference_agent.py` is a small reference showing one way to combine the pieces. It is a starting point, not the answer. Your capstone should go well beyond it.

## Requirements

Your agent must:

1. **Use at least three tools**, including one that reads untrusted content (documents, email or web) and one high-risk action that needs human approval.
2. **Ground answers in your own documents** with retrieval (intermediate Module 03) and cite sources.
3. **Return structured data** somewhere in the flow, validated with Pydantic (intermediate Module 02).
4. **Defend against prompt injection** with taint-aware tool gating and output checks (advanced Module 05), plus the tool security practices from advanced Module 08.
5. **Be observable**: OpenTelemetry spans for agent, model and tool calls, with token counts (advanced Module 03).
6. **Respect a budget**: a per-session cost or token limit, plus at least one optimisation such as caching or routing (advanced Module 06).
7. **Survive failure**: retries with backoff for provider errors, and durable state for anything long-running or waiting for approval (intermediate Module 07, advanced Module 02).
8. **Be evaluated**: at least 20 quality eval cases and 10 red-team attacks, with a CI gate (advanced Module 04).
9. **Be deployed**: a container image built by CI, with health and readiness checks and no secrets in the repo (advanced Module 07).
10. **Work with a free option**: it must run on Ollama or a free tier, so others can try it without paying.

## Milestones

| Week | Milestone | Evidence |
| --- | --- | --- |
| 1 | Problem, users, tools and data chosen; a working agent loop with mocked tests | Short design doc, green CI |
| 2 | Retrieval, structured outputs, guardrails and tool security | Tests for each, first eval run |
| 3 | Tracing, budget, retries, durable approvals; red-team suite and CI gate | Trace screenshots, eval and ASR report |
| 4 | Container, deploy, write-up and demo | Live URL or recorded demo, final report |

## What to hand in

- A public repository with a README that explains the problem, the design, and how to run it with a free provider.
- An **evaluation report**: pass rate, average judge score, attack success rate by category, cost per task, and median latency. Include at least one failure you could not fix, and why.
- A 3 to 5 minute demo video or a live link.
- A short **safety note**: what the agent is allowed to do, what it can never do, and how a person stays in control.

## Assessment rubric

| Area | Weight | Excellent looks like |
| --- | --- | --- |
| Usefulness | 20% | Solves a real problem; eval pass rate and judge scores are reported honestly |
| Safety and security | 25% | Low attack success rate, high-risk actions gated, tool inputs validated, no secrets leaked |
| Engineering quality | 20% | Clean code, offline tests with mocks, CI green, clear README |
| Operations | 15% | Traces, budget limits, retries, health checks, containerised deploy |
| Evaluation rigour | 15% | Realistic cases, red-team coverage across categories, a CI gate |
| Communication | 5% | Clear write-up and demo, honest about limits |

## Step by step to get started

1. Read and run the reference agent's tests:
   ```bash
   pytest modules/09-capstone-project
   ```
2. Copy `starter/capstone_agent.py` into a **new repository** of your own, along with `course_testing.py` and the CI workflow from this repo.
3. Write your design doc (one page): users, top five tasks, tools, data sources, risks, and what "good" means in numbers.
4. Build in small steps, adding tests as you go. Keep CI green.

## Checkpoint quiz (self-review before you submit)

1. Can a prompt injection in one of your documents make the agent take a high-risk action without a person approving?
2. What happens when the model provider returns 429 errors for two minutes?
3. What is your cost per successful task, and where does most of it go?
4. Could a new contributor run your project with no paid account?

<details><summary>What good answers look like</summary>

1. No: the tool gate blocks high-risk tools in tainted contexts, and there is a test proving it.
2. Retries with backoff, then a fallback model or a clear "please try again" message; no crash, no lost state.
3. A measured number from your traces, with a breakdown by model and step, and an optimisation you tried.
4. Yes: the README shows how to run on Ollama or a free tier, and CI needs no keys.
</details>

## Further reading

- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- OWASP, [Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
- OpenAI, [A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [The Twelve-Factor App](https://12factor.net/)
