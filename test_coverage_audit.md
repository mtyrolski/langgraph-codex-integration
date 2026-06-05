# Test Coverage Audit

audit_scope=existing_codebase

## Baseline

The earlier suite covered the main happy paths for `FakeExecutor`, `CodexExecutor`
command construction, graph execution, prompt rendering, OpenAI environment loading,
and a few validation helpers. That was enough for smoke confidence, but thin for a
library whose value is deterministic orchestration around a real process boundary.

## Gaps Found

- `langgraph_codex.execution`: return-code semantics, compatibility aliases,
  mutable fake outputs, dangerous Codex flags, invalid command fields, and workspace
  validation before subprocess execution.
- `langgraph_codex.graph`: context defaults, mutable state copying, execution-vs-backend
  option precedence, retry boundaries, builder aliases, review short-circuiting, and
  serialization of nested dataclass values.
- `langgraph_codex.utils.validation`: pass/fail symmetry, validator short-circuiting,
  missing files, invalid JSON, and failed command details.
- `langgraph_codex.utils.prompts`: scalar/list/dict/dataclass coercion and filtering of
  blank prompt parts.
- `langgraph_codex.utils.open_ai_env`: `.env` precedence, comments, quotes, blank values,
  missing env files, and existing `OPENAI_API_KEY` authorization.
- `langgraph_codex.utils.workspace` and `langgraph_codex.utils.subprocess`: path
  resolution, invalid workspace paths, stdin, nonzero exits, and timeout reporting.

## Changes Implemented

- Expanded the suite from 26 collected tests to 93 collected tests.
- Kept repeated shapes parameterized instead of duplicating long test bodies.
- Added `tests/test_workspace_subprocess.py` for utility boundary behavior.
- Strengthened existing files rather than creating broad duplicate fixtures.
- Fixed `serialize_state_value` so dataclass contents are recursively serialized.

## Remaining Reasonable Limits

- Real Codex integration remains opt-in and skipped unless explicitly enabled.
- Tests assert prompt behavior through rendered output rather than private helper internals.
- CI matrix behavior is validated through workflow configuration and local checks, not by
  trying to emulate every GitHub Actions job locally.
