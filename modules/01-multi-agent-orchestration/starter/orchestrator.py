"""Module 01 starter: a manager agent that plans, delegates to specialists, and uses a bounded reviewer."""

import json
import os
import sys
from dataclasses import dataclass


@dataclass
class Specialist:
    name: str
    description: str
    system_prompt: str

    def run(self, llm, model: str, task: str, context: str) -> str:
        user = f"Task: {task}\n\nWork done so far:\n{context or '(nothing yet)'}"
        reply = llm.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}],
        )
        return reply.choices[0].message.content or ""


DEFAULT_TEAM = [
    Specialist("researcher", "Finds facts, numbers and practical steps.", "You research. List key facts briefly."),
    Specialist("planner", "Turns facts into a step-by-step plan.", "You plan. Write clear numbered steps."),
    Specialist("writer", "Writes polished text for the reader.", "You write warm, plain English for beginners."),
]


class PlanError(ValueError):
    pass


def ask_json(llm, model: str, system: str, user: str) -> dict:
    reply = llm.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(reply.choices[0].message.content or "{}")


def make_plan(llm, model: str, goal: str, team: list[Specialist], max_tasks: int = 4) -> list[dict]:
    """Ask the manager for {"tasks": [{"agent", "task"}]} and validate it strictly."""
    roster = "\n".join(f"- {s.name}: {s.description}" for s in team)
    system = (
        "You are a manager. Break the goal into at most "
        f"{max_tasks} tasks for this team:\n{roster}\n"
        'Reply as JSON: {"tasks": [{"agent": "<name>", "task": "<what to do>"}]}'
    )
    # TODO 1: data = ask_json(llm, model, system, goal); turn json.JSONDecodeError into PlanError.
    # TODO 2: raise PlanError if data["tasks"] is missing, not a list, empty, or longer than max_tasks.
    # TODO 3: raise PlanError if any task is not a dict, names an unknown agent, or has an empty task.
    # TODO 4: return the list of tasks.
    raise NotImplementedError


def orchestrate(
    llm, model: str, goal: str, team: list[Specialist] = DEFAULT_TEAM, max_tasks: int = 4, max_revisions: int = 1
) -> dict:
    trace: list[dict] = []
    # TODO 1: plan = make_plan(...); trace.append({"step": "plan", "tasks": plan})
    # TODO 2: run each task with its specialist, passing the growing context string.
    #         Append {"step": "delegate", "agent", "task", "output"} to trace.
    # TODO 3: synthesise a final answer from the context (one chat call) and trace it.
    # TODO 4: review with ask_json -> {"approved", "feedback"}. Trace {"step": "review", ...}.
    #         If not approved and revisions remain, synthesise again with the feedback
    #         (trace {"step": "revise", ...}). Never exceed max_revisions.
    # TODO 5: return {"final": ..., "approved": ..., "trace": trace}
    raise NotImplementedError


if __name__ == "__main__":
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    llm = OpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
    )
    goal = " ".join(sys.argv[1:]) or "Write a one-page guide to starting a poultry farm in Cross River State"
    result = orchestrate(llm, os.getenv("LLM_MODEL", "llama3.2"), goal)
    for event in result["trace"]:
        print("-", event["step"], event.get("agent", ""), str(event.get("output", event.get("tasks", "")))[:100])
    print(f"\nFINAL (approved={result['approved']}):\n{result['final']}")
