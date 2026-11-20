# Module 01: Multi-agent orchestration

**Time:** about 2 hours. **Before this:** the intermediate level (tool registries, structured outputs, handoffs).

## Objectives

- Know the main multi-agent patterns and when each one is worth its cost.
- Build a **manager** (orchestrator) that plans, delegates to specialists, and combines their work.
- Add a **reviewer** loop with a hard limit on revisions.
- Keep a trace of every step so a multi-agent run can be debugged.

## Concepts in plain English

One agent with many tools gets confused as the job grows: long prompts, too many tools, mixed goals. Splitting the work across **specialists** with short, focused prompts often helps. But every extra agent adds model calls (cost and latency) and new ways to fail. Use more agents only when a single agent measurably struggles.

Common patterns:

| Pattern | How it works | Good for |
| --- | --- | --- |
| **Router / handoff** | A triage agent picks one specialist and passes control | Help desks, clear categories (intermediate Module 05) |
| **Manager / orchestrator** | A manager plans subtasks, calls specialists as tools, then combines results | Research, reports, multi-step jobs |
| **Pipeline** | Fixed order: A then B then C | Predictable processes like extract, check, format |
| **Evaluator / optimiser** | One agent drafts, another critiques, repeat a bounded number of times | Writing, code, anything with a quality bar |
| **Parallel fan-out** | Run independent subtasks at once, then merge | Speed, when subtasks do not depend on each other |

This module builds a **manager with a reviewer**:

1. **Plan:** the manager returns a JSON plan: a short list of `{agent, task}` items. We validate it: only known agents, at most `max_tasks` items.
2. **Delegate:** run each task with its specialist. Each one sees earlier results as context.
3. **Synthesise:** combine the results into one answer.
4. **Review:** a reviewer returns `{approved, feedback}`. If not approved, revise once with the feedback, then stop either way.

Every step is written to a `trace` list. When a run goes wrong, the trace shows which agent said what.

## Step by step

1. Run the finished orchestrator:
   ```bash
   python modules/01-multi-agent-orchestration/solution/orchestrator.py "Write a one-page guide to starting a poultry farm in Cross River State"
   ```
2. In `starter/orchestrator.py`, complete `make_plan()` (with validation) and `orchestrate()`.
3. Test offline:
   ```bash
   TARGET=starter pytest modules/01-multi-agent-orchestration
   ```

## Exercises

1. Run independent tasks in parallel with `concurrent.futures.ThreadPoolExecutor`. Measure the time saved.
2. Give the researcher the RAG tool from the intermediate level so its facts come from documents.
3. Compare against a single agent with all the instructions in one prompt. Use the eval harness to decide which is better, and count the model calls for each.

## Checkpoint quiz

1. Name three multi-agent patterns.
2. Why validate the manager's plan?
3. Why cap reviewer revisions?
4. When is a single agent the better choice?

<details><summary>Answers</summary>

1. Any three of: router or handoff, manager or orchestrator, pipeline, evaluator and optimiser, parallel fan-out.
2. The plan is model output: it can name agents that do not exist or have too many steps.
3. A reviewer can keep finding something to change, which burns money and time with little gain.
4. When the task is small or the extra calls do not measurably improve results.
</details>

## Further reading

- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) and [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- OpenAI Agents SDK, [Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- LangGraph, [Multi-agent systems](https://docs.langchain.com/oss/python/langchain/multi-agent)
- Cognition, [Don't build multi-agents](https://cognition.ai/blog/dont-build-multi-agents) (a useful counterpoint)
