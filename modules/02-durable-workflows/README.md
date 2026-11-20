# Module 02: Durable, long-running workflows

**Time:** about 2 hours.

## Objectives

- Explain why long agent jobs need **durability**: surviving crashes, restarts and deploys.
- Checkpoint each step so a rerun **resumes** instead of starting over.
- Make steps **idempotent**, so running one twice does no harm.
- Pause for **human approval** and resume later, even days later.

## Concepts in plain English

A research agent that runs for 40 minutes, or an onboarding flow that waits two days for a manager to approve, cannot live in one Python process. Servers restart. Laptops sleep. Providers time out at step 37 of 40.

A **durable workflow** saves the result of every completed step to storage. If the process dies, you run it again with the same **run id**. Completed steps are read back from storage instead of being redone; only the unfinished work runs.

Three rules make this safe:

1. **Steps are the unit of saving.** Put each model call or side effect (send email, charge card) in its own named step.
2. **Steps must be idempotent or recorded before acting twice.** "Send the welcome email" must not send two emails if a retry happens. Saving the result, and passing an **idempotency key** (like the run id plus step name) to outside services, prevents duplicates.
3. **Code between steps must be deterministic.** On resume, the workflow code runs again from the top, and the saved results must line up with the same steps. Do not branch on the current time or random numbers outside a step.

**Human in the loop** fits naturally: a step that needs approval checks storage; if no approval is recorded, the workflow stops with a "paused" status. When someone approves, you run it again and it continues from there.

Here we build a small engine on SQLite (part of Python) so you can see every moving part. In production, use a dedicated tool: [Temporal](https://docs.temporal.io/), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [DBOS](https://docs.dbos.dev/), [Restate](https://docs.restate.dev/) or [Vercel Workflow](https://vercel.com/docs/workflow). The ideas carry straight over.

## Step by step

1. Run the demo. It processes a loan application, crashes on purpose at the scoring step the first time, and pauses for approval:
   ```bash
   python modules/02-durable-workflows/solution/durable.py run app-001     # crashes during scoring
   python modules/02-durable-workflows/solution/durable.py run app-001     # resumes, then pauses for approval
   python modules/02-durable-workflows/solution/durable.py approve app-001
   python modules/02-durable-workflows/solution/durable.py run app-001     # finishes
   ```
   Notice that the "summarise" step (a model call) does not run again on resume.
2. In `starter/durable.py`, complete `Workflow.step()` and `Workflow.wait_for_approval()`.
3. Test offline:
   ```bash
   TARGET=starter pytest modules/02-durable-workflows
   ```

## Exercises

1. Add a `retries` argument to `step()` that retries a failing step with backoff before giving up.
2. Add a timeout to approval: if no one approves within 48 hours, take the "rejected" path.
3. Rebuild the loan flow with LangGraph and a SQLite checkpointer, and compare.

## Checkpoint quiz

1. What does a durable workflow save, and why?
2. What is an idempotency key?
3. Why must code between steps be deterministic?
4. How does a paused workflow continue after approval?

<details><summary>Answers</summary>

1. The result of each completed step, so a rerun can skip finished work after a crash.
2. A unique value sent with a side effect so the receiver ignores duplicates of the same request.
3. On resume the code runs again from the top, and saved results must match the same sequence of steps.
4. The approval is recorded in storage, and running the same run id again passes the approval check and moves on.
</details>

## Further reading

- Temporal, [Workflows](https://docs.temporal.io/workflows)
- LangGraph, [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [Human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/interrupts)
- Stripe, [Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- Python docs, [sqlite3](https://docs.python.org/3/library/sqlite3.html)
