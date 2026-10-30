# CI Failure Triage Assistant — Milestone Plan

Oct 29, 2026 · @Tanay · revised for $0 / no new accounts

## Overview

Build a GitHub Action that reads a failed CI run and explains the likely root cause in a PR comment. Prove its accuracy on a hand-labeled benchmark. Ship it in 10 weeks at about 8–10 hours a week, for **$0**, using only a GitHub account and a Google account (Colab).

**Pitch:** When a CI build fails, the bot posts a comment within a couple of minutes. It says what broke, the likely cause, the files to look at, and links to similar past failures and how they were fixed.

**What it proves on a resume:**

- **Product engineering:** a published GitHub Marketplace Action that real repos adopt by adding one YAML file, plus GitHub API integration, safe `workflow_run` handling and a static dashboard.
- **Applied AI:** log reduction, embeddings and retrieval, structured LLM output, and working within rate limits and token budgets.
- **ML rigor:** a hand-labeled benchmark, ablations (including a self-hosted open model on a free GPU vs. a hosted model), and an eval gate. This is where your testing background becomes the differentiator.

**In scope:** GitHub Actions, public repos first (private repos work within the free Actions minutes), and Python/Java/JavaScript/Go test and build logs.

**Out of scope for v1:** other CI systems, automatic fix PRs and fine-tuned models. These are stretch goals.

**Cost rule:** no paid services and no new accounts. Every component below runs on GitHub or Colab for free.

## Architecture

No server. The triage runs as a workflow inside the repo that failed.

```
CI workflow fails
      │  (GitHub fires workflow_run: completed)
      ▼
Triage workflow (GitHub-hosted runner, GITHUB_TOKEN)
  1. parse event, skip non-failures
  2. fetch failed jobs + logs (REST API)
  3. reduce log → excerpt + fingerprint, redact secrets
  4. retrieve similar past failures (ci-triage-data branch)
  5. LLM triage via GitHub Models → validated JSON
  6. post/update PR comment + step summary, append record to data branch
      │
      ▼
GitHub Pages dashboard (static, built from ci-triage-data)

Colab (free GPU): benchmark collection, labeling, eval, ablations, open-model runs
```

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12 (package in `src/ci_triage/`) | The AI/ML ecosystem lives here, and it broadens your profile beyond Java |
| Trigger / compute | `on: workflow_run` on GitHub-hosted runners | Free, no hosting, and GitHub does the queueing |
| GitHub integration | REST API via `httpx` + the workflow's `GITHUB_TOKEN` | No App registration and no stored secrets |
| Validation | Pydantic | Typed event payloads and LLM output |
| LLM (live) | GitHub Models, called with `GITHUB_TOKEN` (`permissions: models: read`) | Free, rate-limited, no API key. Check current models and limits before week 5 |
| LLM (benchmark) | Open 7B-class instruct model, 4-bit, on a Colab T4 with JSON-constrained decoding | No rate limits for 150-case runs, and it gives the "open vs. hosted" ablation |
| Memory | JSONL + embeddings on an orphan `ci-triage-data` branch; numpy cosine search | Replaces Postgres + pgvector; persistent and inspectable |
| Embeddings | `fastembed` (ONNX, CPU) on the runner; sentence-transformers in Colab | Small and fast enough for a runner, and free |
| Dashboard | Next.js static export on GitHub Pages | Builds on your React experience, free hosting |
| Testing | pytest, ruff, mypy; eval gate on a 30-case subset | Shows your QA strength inside an AI project |
| Observability | Step summaries and workflow logs | Built in |
| Dev environment | Edit in VS Code, run in Colab (`notebooks/`), CI on GitHub | Light on your laptop |

**Notebooks vs. package:** all logic lives in `src/ci_triage/`, because the Action, ruff, mypy and pytest need `.py` files. Each notebook clones the repo, installs it and calls the package. Notebooks are for experiments, the benchmark, labeling and charts.

## Week-by-week plan

Four phases: plumbing (1–3), intelligence (4–6), product (7–8), ship (9–10). Labeling starts in week 3, so every prompt change after week 5 is measured.

### Week 1 — Foundations ✅ scaffolded

- [x] Package scaffold: `pyproject.toml`, ruff, mypy, pytest.
- [x] CI workflow for this repo.
- [x] `action.yml` (composite) and a dogfood `triage.yml`. It parses `workflow_run`, skips non-failures, lists the failed jobs and steps, and writes a step summary.
- [x] Sandbox repo template in `examples/sandbox/`: a broken test, a syntax error, a missing dependency and a timeout.
- [x] `notebooks/00_colab_setup.ipynb`.
- [x] Push to GitHub, create the sandbox repo, and point its `triage.yml` at your repo.

**Done when:** a failing sandbox run triggers the triage workflow, and its step summary lists the failed job and step.

### Week 2 — Ingest logs and comment ✅ built, needs a live test

- [x] Download each failed job's log; strip ANSI codes and timestamps.
- [x] Find the PR: use `workflow_run.pull_requests`, then fall back to an `owner:branch` lookup matched on `head_sha` (the list is empty for fork PRs).
- [x] Post one PR comment per workflow and update it on re-runs. A hidden marker makes this idempotent, and its run id stops an older run that finishes late from overwriting a newer one.
- [x] Treat log text as untrusted: show it in a code fence that can't be closed early, and never check out or run PR code in the triage workflow.
- [ ] Live test: open a PR in the sandbox and confirm the comment appears and updates.

**Done when:** every failed sandbox PR run gets one comment with the failing job, step and the last error lines.

### Week 3 — Reduce logs to the failure

- [ ] Cut the log to the failing step. Extract error lines, stack traces and failing test names. Parse JUnit XML artifacts when a repo uploads them.
- [ ] Normalize stack traces (strip line numbers, temp paths, hex addresses) and hash them into a fingerprint.
- [ ] Fixture tests from real logs: pytest, Maven/JUnit, Gradle, Jest, Go.
- [ ] Record the size reduction per log; it becomes a README number.
- [ ] Start the benchmark collection notebook and label the first 30 cases.

**Done when:** each fixture reduces to a short excerpt that still contains the real error.

### Week 4 — Build the benchmark (Colab)

- [ ] Collect 100 failed runs from public repos (grow to 150 later). Save logs immediately, because Actions logs expire, usually after 90 days.
- [ ] Label each case: category, root cause in one sentence, files the fix changed.
- [ ] Freeze a test split you never tune prompts on. Keep the rest for development.
- [ ] `make eval` / `notebooks/eval.ipynb`: runs the pipeline on a split and prints a metrics table.

**Done when:** eval runs end to end in Colab, even if the model step is a stub.

### Week 5 — LLM triage v1

- [ ] **Secret redactor first, with tests.** Nothing reaches a model unredacted.
- [ ] A provider interface with two implementations: GitHub Models (Action) and an open model on the Colab GPU (benchmark).
- [ ] Prompt with the reduced log, the workflow file and a truncated diff. Return JSON (category, root cause, suspected files, suggested fix, confidence), validate it with Pydantic, and retry once.
- [ ] Rate-limit fallback: when the model is unavailable, post the rule-based comment (excerpt, failing tests, fingerprint match).
- [ ] Baseline numbers into `results/`.

**Done when:** the sandbox gets a correct LLM comment, and baseline metrics are recorded.

### Week 6 — Memory and retrieval

- [ ] Store each failure (excerpt, fingerprint, embedding) on the `ci-triage-data` branch. A `concurrency:` group serializes writes.
- [ ] Learn fixes: when a later run on the same branch passes **on a different SHA**, link the commits in between as the fix.
- [ ] Add the top 3 similar past failures and their fixes to the prompt and the comment.
- [ ] Ablation: with vs. without retrieval.

**Done when:** a repeated sandbox failure links to its earlier fix, and the ablation is recorded.

### Week 7 — Flaky tests and feedback

- [ ] Flag a test as flaky when it fails and then passes on the **same SHA** (`run_attempt` > 1). Flaky is detected from run history, not predicted by the LLM.
- [ ] Skip the LLM for known flaky failures and post a short "known flaky" note instead.
- [ ] Feedback: a scheduled workflow polls 👍/👎 reactions on bot comments (GitHub has no reaction webhook) and records them on the data branch.

**Done when:** a deliberately flaky sandbox test is labeled flaky after two runs.

### Week 8 — Dashboard

- [ ] Next.js static export on GitHub Pages: failure list, detail page (excerpt + model output), categories over time, flaky tests, feedback rate.
- [ ] Each PR comment links to its detail page.

**Done when:** you can click from a PR comment to its detail page.

### Week 9 — Harden

- [ ] Fingerprint cache: a repeated failure reuses the earlier triage and skips the model call.
- [ ] Eval gate on a 30-case subset (runs on `main` or manually, to respect rate limits).
- [ ] Polish `action.yml` inputs (watched workflows, comment vs. summary only, model choice) and document permissions.

**Done when:** adding the one YAML file to a fresh repo works with no other setup.

### Week 10 — Launch

- [ ] Publish to the GitHub Marketplace and tag `v1`.
- [ ] Adopt on 3–5 real repos: yours, classmates', and small open-source projects whose maintainers agree.
- [ ] README with real numbers, a 30-second demo GIF and a blog post (Dev.to/Medium accept free sign-in with GitHub or Google).

**Done when:** it's live and used by someone other than you.

## Evaluation plan

**Building the dataset**

1. Pick 15–20 active open-source repos across Python, Java, JavaScript and Go that use GitHub Actions.
2. Find failed PR runs where a later run on the same PR passed **on a different SHA**. A pass on the same SHA is flaky, not fixed.
3. Save the failing log, workflow file, PR diff and fix commits right away. Logs expire.
4. Label: category, a one-sentence root cause, and the files the fix changed.
5. No category should be more than about a third of the set.

Budget about 4–5 minutes a case. Store labels as JSONL in `data/labels/`. Keep raw logs out of git (`data/raw/` is gitignored) unless they are redacted.

**Categories (predicted by the LLM):** test failure, compile/build error, dependency or install, lint/format, timeout or infrastructure, config/workflow error. **Flaky** is detected separately from run history.

**Metrics**

| Metric | How it's measured | Automatic? |
| --- | --- | --- |
| Category accuracy | Predicted category matches the label | Yes |
| File localization hit@3 | A fix-changed file is in the top 3 suspected files | Yes |
| Root-cause correctness | You grade each explanation (correct, partial, wrong) without seeing which configuration produced it | No |
| Retrieval recall@5 | For repeat failures, the earlier one is in the top 5 | Yes |
| Latency p50 / p95 (s) | Run completed → comment posted | Yes |
| Tokens per triage | Input + output tokens (the cost proxy, since the run is free) | Yes |
| Helpful rate | 👍 share of reacted comments | Yes, after launch |

**Ablations (one row each in the README):**

- Full log vs. reduced log.
- With vs. without retrieval.
- Open 7B model on Colab vs. GitHub Models' hosted model.
- LLM vs. the rule-based fallback.

**Rules that keep it honest:**

- Never tune prompts on the test split.
- Report weak numbers too.
- Note that public-repo fixes may be in the models' training data. If you can, report failures that happened after the model's training cutoff separately.

## README outline

1. Name + one-line pitch, with badges (CI, license, Marketplace).
2. Demo GIF (≤30 s): a red run, then the comment appears.
3. Results table from the frozen test split, with links to the eval notebook and dataset.
4. How it works: the architecture diagram, one sentence per stage.
5. Quickstart: the one YAML file.
6. Configuration: Action inputs.
7. Evaluation: dataset, ablations, how to reproduce it in Colab.
8. Design decisions:
   - why an Action instead of a hosted App ($0, no secrets)
   - why log reduction comes first
   - why a git branch for storage
   - the GitHub Models vs. open-model trade-off
   - safe `workflow_run` handling
9. Privacy and security: what goes to the model, redaction, and what's stored on the data branch.
10. Limitations, with real benchmark examples.
11. Roadmap, contributing, MIT license.

## Resume bullets (fill at launch)

- Built and published a GitHub Action that triages failed CI runs with an LLM and retrieval over past fixes. Adopted by \[N\] repositories, \[N\] failures triaged.
- Designed a log-reduction pipeline that cut model input by \[X\]% and raised root-cause accuracy from \[A\]% to \[B\]% on a \[N\]-case hand-labeled benchmark.
- Benchmarked a 4-bit open 7B model on a free GPU against a hosted model: \[accuracy, latency, tokens\]. Added an eval gate in CI to block regressions.
- Implemented embedding search over past failures, improving file localization hit@3 by \[X\] points.

## Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| GitHub Models daily limit or model changes | Rule-based comment fallback; fingerprint cache; benchmark runs on the Colab open model |
| Logs too long for the model | The week 3 reducer; else the last error block + failing test names |
| Secrets in logs | Redact before any model call; never log raw prompts |
| Logs expire before collection | Collect and save immediately; collect over several days |
| API rate limits while collecting | Cache responses on Google Drive; spread collection out |
| Colab session resets | Code lives on GitHub; datasets and results saved to Drive or committed |
| Labeling takes longer | Start at 100 cases; grow after launch |
| Scope creep | Anything not in weeks 1–10 goes in `later.md` |

## Stretch goals

- Fine-tune a small classifier for the category on the Colab GPU and compare it to the LLM.
- A draft fix PR for lint/format failures.
- Weekly digest issue per repo, from a scheduled workflow.
