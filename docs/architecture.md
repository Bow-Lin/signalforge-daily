# Architecture

## Overview
`news_collection` is a Python 3.10+ project using a `src/` package layout. It provides command-line workflows for paper collection, blog tracking, and AI-assisted RSS digest generation.

## Main Components
- `src/news_collection/cli.py`: paper/news collection CLI driven by `config.json` or command-line arguments.
- `src/news_collection/graph.py`: LangGraph pipeline orchestration for collection and selection.
- `src/news_collection/arxiv.py`: arXiv search integration.
- `src/news_collection/storage.py`: paper result and metadata storage helpers.
- `src/news_collection/pdf_tools.py`: PDF download and evidence extraction helpers.
- `src/news_collection/blog_cli.py`: blog synchronization CLI.
- `src/news_collection/blog_tracker/`: blog tracking domain logic, storage, and source adapters.
- `src/news_collection/digest_cli.py`: AI daily digest CLI.
- `src/news_collection/digest.py`: RSS/blog fetch, scoring, summarization, and Markdown report rendering.
- `src/news_collection/digest_feeds.py`: default digest source list.
- `scripts/graph_viz.py`: graph visualization utility.

## Data and Generated Outputs
Generated outputs are local project artifacts and should not be treated as source:
- `paper/`: paper metadata, PDF cache, and selected PDFs.
- `blog/`: blog sync outputs and source tracking.
- `output/`: digest Markdown reports.
- `logs/`: local runtime logs.

## External Services
- iFlow/OpenAI-compatible AI API via `IFLOW_API_KEY` or CLI argument.
- Optional Langfuse telemetry through environment variables.
- arXiv and RSS/blog HTTP sources.

## Harness Boundary
The harness lives in `AGENTS.md`, `current-task.md`, `docs/`, `.harness/`, `skills/`, and `scripts/`. Harness initialization must not change business code under `src/`.
