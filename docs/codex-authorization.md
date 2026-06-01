# Codex Authorization Guide

This repository has two execution modes:

- Offline mode: deterministic examples, unit tests, linting, typing, packaging, and normal CI do not require Codex credentials.
- Real Codex mode: examples `02` through `10` and `tests/integration` call `CodexExecutor`, which shells out to `codex exec`.

## Local Secrets

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Set the secret value locally:

```text
OPEN_AI_SECRET_KEY=...
OPEN_AI_KEY_NAME=local-codex
OPEN_AI_MODEL=
```

The real Codex examples and integration tests load `.env` and map `OPEN_AI_SECRET_KEY` to `OPENAI_API_KEY` for the Codex subprocess if `OPENAI_API_KEY` is not already set.

`OPEN_AI_KEY_NAME` is a human-readable key label. It is printed only as a label and is not treated as a secret.

By default, real examples and integration tests let the Codex CLI choose its configured model. Set `OPEN_AI_MODEL` only when you explicitly want to override the CLI default for these examples/tests.

Do not print this value. Do not paste it into prompts, issue comments, test output, CI logs, or agent instructions.

## Git Ignore Policy

The repository ignores:

```text
.env
.env.*
```

It explicitly allows:

```text
.env.example
```

The example file documents variable names only. It must never contain real credentials.

## Running Real Codex Locally

Install Codex CLI if it is not already available:

```bash
npm install -g @openai/codex
```

Run all offline checks:

```bash
make check
```

Run real Codex examples and integration tests:

```bash
make check-codex
```

Run only real Codex tests:

```bash
make test-codex
```

The real tests require:

```text
LANGGRAPH_CODEX_RUN_REAL_CODEX=1
OPEN_AI_SECRET_KEY or OPENAI_API_KEY
OPEN_AI_MODEL when you explicitly want a non-default Codex model
codex on PATH
```

`make test-codex` sets `LANGGRAPH_CODEX_RUN_REAL_CODEX=1` automatically. The tests load `.env`.

## CI Authorization

Default pull request and `main` CI are offline. They do not require Codex credentials and do not run real Codex examples.

Real Codex CI is opt-in through manual workflow dispatch:

1. Add `OPEN_AI_SECRET_KEY` as a GitHub Actions secret.
2. Open the CI workflow manually.
3. Enable `run-real-codex`.
4. Start the workflow.

The real Codex job installs the Codex CLI with:

```bash
npm install -g @openai/codex
```

It sets:

```text
LANGGRAPH_CODEX_RUN_REAL_CODEX=1
OPEN_AI_SECRET_KEY=${{ secrets.OPEN_AI_SECRET_KEY }}
OPEN_AI_KEY_NAME=github-actions
OPEN_AI_MODEL=
OPENAI_API_KEY=${{ secrets.OPEN_AI_SECRET_KEY }}
```

## Multi-Agent Safety

When using sub-agents or parallel workers:

- Do not send secret values to agents.
- Do not include `.env` contents in prompts.
- Do not ask sub-agents to inspect or print `.env`.
- Prefer running real Codex checks in the parent session after sub-agents finish.
- If a secret is copied into the shared workspace while sub-agents are running, stop the agents or confirm they do not need workspace access before continuing.
- Keep real Codex tests opt-in and explicit.

Sub-agents can safely edit code, docs, and tests without receiving credentials. The parent agent should own any step that requires local secrets.

## Executor Safety Defaults

`CodexExecutor` rejects these dangerous flags:

```text
--dangerously-bypass-approvals-and-sandbox
--dangerously-bypass-hook-trust
```

It uses the package defaults:

```text
sandbox=workspace-write
approval_policy=never
timeout_seconds=900
```

Examples use temporary workspaces where possible and instruct Codex not to print secrets.
