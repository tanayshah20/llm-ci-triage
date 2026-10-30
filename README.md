# ci-triage

A GitHub Action that reads a failed CI run, explains the likely root cause, and comments on the pull request. It runs entirely on GitHub: no server, no API keys, no paid services.

> **Status: week 2 of 10.** The Action downloads each failed job's log and posts one PR comment per workflow, showing the failing step and the last error lines. It updates that comment on later runs. Log reduction and LLM triage land in the coming weeks. See the [milestone plan](CI%20Failure%20Triage%20Assistant%20—%20Milestone%20Plan.md).

## Use it in a repo

Add `.github/workflows/triage.yml` to the **default branch** (`workflow_run` only fires from there):

```yaml
name: CI Triage
on:
  workflow_run:
    workflows: [CI]          # the name of the workflow to watch
    types: [completed]
permissions:
  actions: read
  contents: read
  pull-requests: write
jobs:
  triage:
    if: github.event.workflow_run.conclusion == 'failure'
    runs-on: ubuntu-latest
    steps:
      - uses: YOUR_GITHUB_USERNAME/llm-ci-triage@main
```

## Develop

The code is a normal Python package in `src/ci_triage/`; notebooks in `notebooks/` clone the repo and call it.

**In Google Colab:** open `notebooks/00_colab_setup.ipynb`, set `REPO_URL`, and run all cells.

**Locally:**

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
ruff check . && mypy src tests && pytest
```

`examples/sandbox/` is a ready-made repo whose jobs fail on purpose (broken test, syntax error, missing dependency, timeout). Copy it into a new public repo to exercise the Action.

## License

MIT
