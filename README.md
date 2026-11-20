# AI Agents: Advanced

[![CI](https://github.com/dukemawex/ai-agents-advanced/actions/workflows/ci.yml/badge.svg)](https://github.com/dukemawex/ai-agents-advanced/actions/workflows/ci.yml)

A hands-on course by **Dukers Ltd**. Build agents you can trust in production: multi-agent orchestration, durable workflows, tracing, evals and red-teaming, prompt-injection defence, cost control, containers and CI, and tool security, finished with a capstone project.

**Who it is for:** You have finished the intermediate level, or you have shipped an agent before and want to make it robust, observable and secure.

By the end you will be able to design, test, secure, observe and deploy an agent system, and prove its quality and safety with numbers.

## Modules

| # | Module | What you build and learn | Time |
| --- | --- | --- | --- |
| 01 | [Multi-agent orchestration](modules/01-multi-agent-orchestration/) | Manager and specialists, validated plans, bounded review | 2 h |
| 02 | [Durable, long-running workflows](modules/02-durable-workflows/) | Checkpoints on SQLite, resume after crash, human approval | 2 h |
| 03 | [Observability and tracing](modules/03-observability-tracing/) | OpenTelemetry spans with GenAI semantic conventions | 90 min |
| 04 | [Advanced evals and red-teaming](modules/04-evals-and-red-teaming/) | LLM judges, canary tokens, attack success rate, CI gates | 2 h |
| 05 | [Guardrails and prompt-injection defence](modules/05-guardrails-prompt-injection/) | Spotlighting, taint-aware tool gating, output checks | 2 h |
| 06 | [Cost and latency optimisation](modules/06-cost-latency-optimization/) | Caching, routing, cascades, trimming, budgets | 90 min |
| 07 | [Production deploy](modules/07-production-deploy/) | Health and readiness, JSON logs, rate limits, Docker, CI to GHCR | 2 h |
| 08 | [Security of tool use](modules/08-tool-use-security/) | Sandboxed files, no-shell commands, SSRF checks, audit logs | 2 h |
| 09 | [Capstone project](modules/09-capstone-project/) | Spec, milestones, rubric and a reference agent | 2 to 4 weeks |

Then build your capstone and share it.

## Quick start

```bash
git clone https://github.com/dukemawex/ai-agents-advanced.git
cd ai-agents-advanced
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                 # Windows: copy .env.example .env
pytest                               # offline tests, no API key needed
```

Then pick a model provider in `.env`. The default is [Ollama](https://ollama.com), which is free and runs on your own computer (`ollama pull llama3.2`). A free [Groq](https://console.groq.com) key works too, as do OpenRouter and OpenAI. Every lesson uses the OpenAI-compatible API, so you switch provider by editing `.env`, not code.

## How each module works

```
modules/NN-topic/
  README.md     objectives, plain-English concepts, step by step, exercises, quiz, further reading
  starter/      code with TODOs for you to finish
  solution/     a finished, working version
  tests/        offline tests; the model is replaced by a scripted fake
```

- Run a finished example: `python modules/NN-topic/solution/<file>.py`
- Check your own work: `TARGET=starter pytest modules/NN-topic` (PowerShell: `$env:TARGET="starter"; pytest modules/NN-topic`)
- Run everything: `pytest`

The tests use `FakeLLM` from [`course_testing.py`](course_testing.py). It returns scripted replies in the exact shape the OpenAI library returns, so tests are fast, free and give the same result every time. CI runs `ruff` and these tests on every push, with no secrets.

## Free and paid providers

| Provider | Cost to start | `LLM_BASE_URL` |
| --- | --- | --- |
| Ollama (local) | Free | `http://localhost:11434/v1` |
| Groq | Free tier with rate limits | `https://api.groq.com/openai/v1` |
| OpenRouter | Some free models | `https://openrouter.ai/api/v1` |
| OpenAI | Paid | `https://api.openai.com/v1` |

Free tiers, model names and prices change often. Check each provider's site before relying on one.

## Part of a three-level course

| Level | Repository |
| --- | --- |
| Start here: overview and learning path | [ai-agents-course](https://github.com/dukemawex/ai-agents-course) |
| Beginner | [ai-agents-beginner](https://github.com/dukemawex/ai-agents-beginner) |
| Intermediate | [ai-agents-intermediate](https://github.com/dukemawex/ai-agents-intermediate) |
| Advanced | [ai-agents-advanced](https://github.com/dukemawex/ai-agents-advanced) |

## Contributing and help

Found a bug or got stuck? Open an issue using one of the templates. Please never paste API keys or your `.env` file. See [CONTRIBUTING.md](CONTRIBUTING.md) and the hub's [code of conduct](https://github.com/dukemawex/ai-agents-course/blob/main/CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE), copyright Dukers Ltd. Third-party libraries and services keep their own licenses and terms.
