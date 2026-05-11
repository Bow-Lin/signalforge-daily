# Coding Guidelines

## Python
- Target Python 3.10+.
- Follow PEP 8 with 4-space indentation.
- Use `snake_case` for functions and variables.
- Use `PascalCase` for classes.
- Add explicit type hints on public functions and dataclasses.
- Keep imports grouped as standard library, third-party, then local package imports.
- Prefer small focused functions over broad multi-purpose helpers.

## CLI and Configuration
- Prefer CLI option names that map directly to internal parameter names, for example `--max-results` to `max_results`.
- Keep `config.json` as non-secret defaults only.
- Load secrets from CLI args, environment variables, or `.env` where the existing code supports it.

## Tests
- Place tests under `tests/`.
- Name test files `test_*.py`.
- For new behavior, include a success-path test and at least one edge or failure case when practical.
- Keep tests deterministic by mocking network and AI providers.

## Generated Artifacts
Do not commit generated data from `paper/`, `blog/`, `output/`, `logs/`, caches, or virtual environments.

## Harness Files
- Keep protocol files concise and operational.
- Record durable decisions in `docs/decisions.md`.
- Record repeated failures and workarounds in `docs/error-journal.md`.
