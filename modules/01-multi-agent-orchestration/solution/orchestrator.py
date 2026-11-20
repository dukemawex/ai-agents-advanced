"""Module 01: a manager agent that plans, delegates to specialists, and uses a bounded reviewer."""

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
    try:
        data = ask_json(llm, model, system, goal)
    except json.JSONDecodeError as exc:
        raise PlanError("plan was not valid JSON") from exc
    tasks = data.get("tasks")
    names = {s.name for s in team}
    if not isinstance(tasks, list) or not tasks:
        raise PlanError("plan has no tasks")
    if len(tasks) > max_tasks:
        raise PlanError(f"plan has {len(tasks)} tasks; the limit is {max_tasks}")
    for item in tasks:
        if not isinstance(item, dict) or item.get("agent") not in names or not item.get("task"):
            raise PlanError(f"invalid task: {item!r}")
    return tasks


def orchestrate(
    llm, model: str, goal: str, team: list[Specialist] = DEFAULT_TEAM, max_tasks: int = 4, max_revisions: int = 1
) -> dict:
    trace: list[dict] = []
    by_name = {s.name: s for s in team}
    plan = make_plan(llm, model, goal, team, max_tasks)
    trace.append({"step": "plan", "tasks": plan})

    context = ""
    for item in plan:
        output = by_name[item["agent"]].run(llm, model, item["task"], context)
        trace.append({"step": "delegate", "agent": item["agent"], "task": item["task"], "output": output})
        context += f"\n[{item['agent']}] {output}"

    def synthesise(feedback: str = "") -> str:
        extra = f"\nReviewer feedback to address: {feedback}" if feedback else ""
        reply = llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Combine the team's work into one clear final answer."},
                {"role": "user", "content": f"Goal: {goal}\nTeam work:{context}{extra}"},
            ],
        )
        return reply.choices[0].message.content or ""

    final = synthesise()
    trace.append({"step": "synthesise", "output": final})
    for revision in range(max_revisions + 1):
        review = ask_json(
            llm,
            model,
            'You review answers. Reply as JSON: {"approved": true|false, "feedback": "<short>"}',
            f"Goal: {goal}\nAnswer:\n{final}",
        )
        approved = bool(review.get("approved"))
        trace.append({"step": "review", "approved": approved, "feedback": review.get("feedback", "")})
        if approved or revision == max_revisions:
            break
        final = synthesise(review.get("feedback", ""))
        trace.append({"step": "revise", "output": final})
    return {"final": final, "approved": approved, "trace": trace}


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
