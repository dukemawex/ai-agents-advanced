"""Module 02: a tiny durable workflow engine on SQLite, with checkpoints and human approval."""

import json
import os
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS steps (run_id TEXT, name TEXT, result TEXT, PRIMARY KEY (run_id, name));
CREATE TABLE IF NOT EXISTS approvals (run_id TEXT, name TEXT, approved INTEGER, PRIMARY KEY (run_id, name));
"""


class PausedForApproval(Exception):
    def __init__(self, run_id: str, name: str):
        super().__init__(f"run {run_id} is waiting for approval of '{name}'")
        self.run_id, self.name = run_id, name


class Rejected(Exception):
    pass


class Workflow:
    def __init__(self, db_path: str | Path, run_id: str):
        self.db = sqlite3.connect(db_path)
        self.db.executescript(SCHEMA)
        self.run_id = run_id
        self.log: list[str] = []

    def idempotency_key(self, name: str) -> str:
        """Pass this to outside services so a retried side effect is not applied twice."""
        return f"{self.run_id}:{name}"

    def step(self, name: str, fn: Callable[[], Any]) -> Any:
        """Return the saved result if this step already finished; otherwise run fn() and save it."""
        row = self.db.execute("SELECT result FROM steps WHERE run_id=? AND name=?", (self.run_id, name)).fetchone()
        if row is not None:
            self.log.append(f"skip {name} (saved)")
            return json.loads(row[0])
        result = fn()  # if this raises, nothing is saved and a rerun will try again
        with self.db:
            self.db.execute("INSERT INTO steps VALUES (?, ?, ?)", (self.run_id, name, json.dumps(result)))
        self.log.append(f"ran {name}")
        return result

    def wait_for_approval(self, name: str) -> None:
        """Pause the run until a person approves `name`. Raise Rejected if they said no."""
        row = self.db.execute(
            "SELECT approved FROM approvals WHERE run_id=? AND name=?", (self.run_id, name)
        ).fetchone()
        if row is None:
            self.log.append(f"paused at {name}")
            raise PausedForApproval(self.run_id, name)
        if not row[0]:
            raise Rejected(f"'{name}' was rejected")
        self.log.append(f"approved {name}")

    @staticmethod
    def record_approval(db_path: str | Path, run_id: str, name: str, approved: bool) -> None:
        db = sqlite3.connect(db_path)
        db.executescript(SCHEMA)
        with db:
            db.execute("INSERT OR REPLACE INTO approvals VALUES (?, ?, ?)", (run_id, name, int(approved)))


# ---------- an example workflow: a small loan application ----------


def loan_workflow(wf: Workflow, application: dict, summarise: Callable[[dict], str], score: Callable[[dict], int]):
    summary = wf.step("summarise", lambda: summarise(application))
    risk = wf.step("score", lambda: score(application))
    if risk >= 70:  # deterministic branch on saved data only
        wf.wait_for_approval("manager_review")
    notice = wf.step("notify", lambda: f"sent decision to {application['email']} key={wf.idempotency_key('notify')}")
    return {"summary": summary, "risk": risk, "notice": notice}


if __name__ == "__main__":
    db_path = Path(os.getenv("WORKFLOW_DB", "workflows.sqlite"))
    args = sys.argv[1:]
    command = args[0] if args else "run"
    run_id = args[1] if len(args) > 1 else "app-001"
    if command == "approve":
        Workflow.record_approval(db_path, run_id, "manager_review", True)
        print("approved", run_id)
        raise SystemExit(0)

    crash_flag = db_path.with_suffix(".crashed")

    def fake_summarise(app: dict) -> str:
        print("  (calling the model to summarise... this costs money, so it should only happen once)")
        return f"{app['name']} wants NGN {app['amount']:,} for {app['purpose']}."

    def flaky_score(app: dict) -> int:
        if not crash_flag.exists():
            crash_flag.touch()
            raise ConnectionError("simulated crash during scoring")
        return 75

    wf = Workflow(db_path, run_id)
    app = {"name": "Ada", "amount": 2_500_000, "purpose": "a cassava processing machine", "email": "ada@example.com"}
    try:
        print(loan_workflow(wf, app, fake_summarise, flaky_score))
    except PausedForApproval as paused:
        print("PAUSED:", paused, "\nApprove with: python durable.py approve", run_id)
    except ConnectionError as err:
        print("CRASHED:", err, "\nRun the same command again to resume.")
    print("log:", wf.log)
