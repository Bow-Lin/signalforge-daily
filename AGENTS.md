# Repository Guidelines

## Project Structure & Module Organization
The codebase uses a `src/` layout:
- `src/news_collection/`: core package and CLIs (`cli.py`, `blog_cli.py`, `digest_cli.py`), graph pipeline, storage, and PDF helpers.
- `src/news_collection/blog_tracker/`: blog tracking domain logic and source adapters.
- `src/news_collection/digest.py`: Python daily digest pipeline (RSS fetch -> AI scoring -> summarization -> markdown report).
- `src/news_collection/digest_feeds.py`: default RSS sources list for digest.
- `scripts/graph_viz.py`: graph visualization utility.
- `config.json`: example runtime config.

Generated outputs are ignored by git and should stay local:
- `paper/` (paper results, PDF cache, selected PDFs)
- `blog/` (blog sync outputs and source tracking)
- `output/` (digest reports)

## Build, Test, and Development Commands
- Preferred environment setup: `uv sync`
- `uv run python -m news_collection.cli --config config.json`: run paper/news collection from config.
- `uv run python -m news_collection.blog_cli --source all`: sync all supported blog sources.
- `uv run python -m news_collection.digest_cli --hours 24 --top-n 15 --lang zh`: generate daily digest report.
- `uv run python scripts/graph_viz.py --format mermaid --out /tmp/graph.mmd`: render graph definition.
- `uv run python -m pytest -q`: run tests.
- Alternative (pip): `pip install -r requirements.txt && pip install -e .`

## Coding Style & Naming Conventions
- Python 3.10+; follow PEP 8 with 4-space indentation.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and explicit type hints on public functions.
- Keep imports grouped (stdlib, third-party, local) and favor small, focused functions.
- Prefer CLI/config argument names that map directly to internal parameter names (for example `--max-results` -> `max_results`).

## Testing Guidelines
- Framework: `pytest` (declared in `pyproject.toml` dev dependencies).
- Place tests under a top-level `tests/` directory using `test_*.py` naming.
- Focus on behavior of CLI entry points, graph flow decisions, storage read/write paths, and digest parsing/report rendering.
- For new features, add at least one success-path test and one failure/edge-case test.

## Commit & Pull Request Guidelines
- Keep commit messages short, imperative, and scoped (examples from history: `add rss`, `fix arxiv search bug`, `refactor: ...`).
- Prefer one logical change per commit.
- PRs should include:
  - What changed and why.
  - How to run/verify (`python -m ...`, `pytest`).
  - Any config/env changes (for example `IFLOW_API_KEY`, Langfuse keys).
  - Sample output paths if behavior affects `paper/` or `blog/` artifacts.

## Security & Configuration Tips
- Store secrets in environment variables or `.env`; never commit credentials.
- Treat `config.json` as non-secret defaults only; keep API keys out of tracked files.

## Digest Notes
- AI key source priority:
  - CLI arg: `--iflow-key`
  - env: `IFLOW_API_KEY` (loaded via `.env` when available)
- Known runtime issue:
  - If RSS fetch logs show proxy errors to `127.0.0.1:7890`, unset proxy env vars or start local proxy.
- Digest module includes response-shape fallbacks for OpenAI-compatible providers to avoid crashes on partial/variant `choices` payloads.
