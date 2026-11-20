import pytest

from course_testing import load

m = load("02-durable-workflows", "durable.py")
APP = {"name": "Ada", "amount": 100, "purpose": "tools", "email": "ada@example.com"}


class Counter:
    def __init__(self, fail_first=0, value=50):
        self.calls, self.fail_first, self.value = 0, fail_first, value

    def __call__(self, app):
        self.calls += 1
        if self.calls <= self.fail_first:
            raise ConnectionError("crash")
        return self.value


def test_resume_after_crash_skips_finished_steps(tmp_path):
    db = tmp_path / "wf.sqlite"
    summarise = Counter(value="summary")
    score = Counter(fail_first=1, value=10)
    with pytest.raises(ConnectionError):
        m.loan_workflow(m.Workflow(db, "r1"), APP, summarise, score)
    wf = m.Workflow(db, "r1")
    result = m.loan_workflow(wf, APP, summarise, score)
    assert result["risk"] == 10
    assert summarise.calls == 1  # the expensive step ran only once
    assert wf.log[0] == "skip summarise (saved)"
    assert "r1:notify" in result["notice"]


def test_pause_then_approve_then_finish(tmp_path):
    db = tmp_path / "wf.sqlite"
    score = Counter(value=90)
    with pytest.raises(m.PausedForApproval):
        m.loan_workflow(m.Workflow(db, "r2"), APP, Counter(value="s"), score)
    with pytest.raises(m.PausedForApproval):  # still paused: no approval yet
        m.loan_workflow(m.Workflow(db, "r2"), APP, Counter(value="s"), score)
    m.Workflow.record_approval(db, "r2", "manager_review", True)
    result = m.loan_workflow(m.Workflow(db, "r2"), APP, Counter(value="s"), score)
    assert result["risk"] == 90 and score.calls == 1


def test_rejection(tmp_path):
    db = tmp_path / "wf.sqlite"
    m.Workflow.record_approval(db, "r3", "manager_review", False)
    with pytest.raises(m.Rejected):
        m.loan_workflow(m.Workflow(db, "r3"), APP, Counter(value="s"), Counter(value=99))


def test_runs_are_isolated(tmp_path):
    db = tmp_path / "wf.sqlite"
    a, b = m.Workflow(db, "a"), m.Workflow(db, "b")
    assert a.step("x", lambda: 1) == 1
    assert b.step("x", lambda: 2) == 2
    assert m.Workflow(db, "a").step("x", lambda: 3) == 1
