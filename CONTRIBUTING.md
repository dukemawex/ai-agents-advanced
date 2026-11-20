# Contributing

Thank you for helping make this course better. The full contribution guide and code of
conduct live in the course hub:

- [Contribution guide](https://github.com/dukemawex/ai-agents-course/blob/main/CONTRIBUTING.md)
- [Code of conduct](https://github.com/dukemawex/ai-agents-course/blob/main/CODE_OF_CONDUCT.md)

Quick checks before you open a pull request:

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
pytest
```

Every module needs a README, a `starter/` folder, a `solution/` folder and offline tests in
`tests/` that use `FakeLLM` from `course_testing.py`, so CI never needs an API key.
