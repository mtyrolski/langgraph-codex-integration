# Examples

All examples are runnable with `uv run python <file>`. Examples 00 and 01 are offline and run in normal CI. Examples 02-10 use the real `CodexExecutor` and require the Codex CLI to be installed and authenticated.

## First Run

```bash
make examples
```

## Example Index

| File | Scenario | Shows |
| --- | --- | --- |
| `00_context_only_graph.py` | Render a prompt from explicit state | Context-only graph |
| `01_fake_executor_graph.py` | Run a fake executor | Executor abstraction |
| `02_codex_executor_graph.py` | Run real Codex | Opt-in `codex exec` executor |
| `03_retry_graph.py` | Retry after execution failure | Real executor with deterministic retry routing |
| `04_custom_validation.py` | Validate execution output | Real executor with custom validators |
| `05_quickstart.py` | Minimal end-to-end flow | Real execution graph usage |
| `06_customer_feedback_triage.py` | Triage customer feedback CSV data | Real executor summary with deterministic context |
| `07_dataset_quality_profile.py` | Profile order data quality | Real executor data inspection |
| `08_policy_review_retry.py` | Review a policy draft | Real executor retry until structured output passes validation |
| `09_research_digest.py` | Synthesize research notes | Real executor note digest workflow |
| `10_service_config_review.py` | Review JSON service configuration | Real executor remediation validation |

## Real-Task Pattern

The real Codex examples follow the same structure:

1. Create a temporary sample workspace.
2. Read real files from that workspace with deterministic Python.
3. Store explicit context, artifacts, files, and metadata in graph state.
4. Render a stable Markdown prompt.
5. Call `CodexExecutor` for the execution step.
6. Validate outputs deterministically.

Run the offline examples with `make examples`. Run the real Codex examples with `make examples-codex`.

See `docs/codex-authorization.md` for `.env`, `OPEN_AI_SECRET_KEY`, `OPEN_AI_KEY_NAME`, `OPEN_AI_MODEL`, and multi-agent safety guidance.
