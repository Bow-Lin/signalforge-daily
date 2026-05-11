# Decisions

## Decision Log

### 2026-05-11 - Initialize Standard Project Harness
- Status: Accepted
- Context: The repository is a long-lived Python project with multiple CLIs, generated outputs, AI/network integrations, and agent-assisted development.
- Decision: Use a Standard Harness with protocol, state, verification, skills, and boundary scripts.
- Consequences: Future sessions should start with `/start`, record plans and verification evidence, and use `/handoff` before ending substantive work.

### 2026-05-11 - Keep External Skill Checkout Ignored
- Status: Accepted
- Context: `skills/ai-daily-digest/` is an external git checkout and should not be mixed into this repository history.
- Decision: Ignore only `skills/ai-daily-digest/` rather than the full `skills/` directory, so project harness skills can be tracked.
- Consequences: Harness skills under `skills/start`, `skills/plan`, `skills/review`, `skills/commit`, and `skills/handoff` remain eligible for version control.

## Template

### YYYY-MM-DD - Title
- Status: Proposed | Accepted | Superseded
- Context:
- Decision:
- Consequences:
