# News Collection (LangGraph)

Collect topic-related content with LangGraph. Currently implements paper collection via arXiv.
Uses a two-step LLM plan-and-select flow with sequential tool execution and PDF evidence.

## Latest Updates (2026-02-25)

- Added Python AI daily digest pipeline (`news_collection.digest_cli`) aligned with the `ai-daily-digest` skill.
- Added built-in RSS source list (`92` feeds) and report generation with:
  - Top 3 picks
  - Category grouping
  - Mermaid charts
  - ASCII keyword chart
  - Tag cloud
- Added resilient AI response parsing for iFlow/OpenAI-compatible responses.
- Added digest unit tests under `tests/test_digest.py`.

## Setup

Python requirement: `>=3.10` (recommended: use `uv`).

### Option A (Recommended): uv

1) Sync environment:

```bash
uv sync
```

2) Set API key:

```bash
export IFLOW_API_KEY=your_key
```

3) Run commands with `uv run`:

```bash
uv run python -m news_collection.digest_cli --hours 24 --top-n 15 --lang zh
```

### Option B: pip

1) Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

2) Set API key:

```bash
export IFLOW_API_KEY=your_key
```

3) (Optional) Enable Langfuse:

```bash
export LANGFUSE_PUBLIC_KEY=your_public_key
export LANGFUSE_SECRET_KEY=your_secret_key
export LANGFUSE_HOST=https://cloud.langfuse.com
```

## Usage

Run a paper collection:

```bash
python -m news_collection.cli \
  --topic "RTL 代码生成 且使用cvdp数据集或RealBench数据集" \
  --requirements "使用cvdp数据集或RealBench数据集" \
  --content-type paper \
  --start "2025-09-01" \
  --end "2026-01-15" \
  --tz "Asia/Shanghai" \
  --iflow-model "qwen3-max" \
  --max-results 5 \
  --pdf-max-chars 16000
```

You can also run via a config file:

```bash
python -m news_collection.cli --config /home/deming/work/news_collection/config.json
```

Collected items are saved under `paper/papers_latest.jsonl`.
Downloaded PDFs are cached under `paper/pdf_cache/`.
Selected PDFs are copied to `paper/pdfs/`.

Run blog tracker:

```
python -m news_collection.blog_cli --source all
```

Blog outputs are saved under `blog/`, and sources are tracked in `blog/sources.txt` (first line is `last_run_at\t<iso>`).

Run AI daily digest (Python):

```bash
uv run python -m news_collection.digest_cli --hours 24 --top-n 15 --lang zh
```

Digest output is saved under `output/digest-YYYYMMDD.md` by default.

Advanced digest options:

```bash
uv run python -m news_collection.digest_cli \
  --hours 24 \
  --top-n 15 \
  --lang zh \
  --output ./output/digest-$(date +%Y%m%d).md \
  --feed-concurrency 10 \
  --ai-batch-size 10 \
  --ai-retries 1 \
  --max-ai-articles 120
```

Optional custom feeds file:

```bash
uv run python -m news_collection.digest_cli --feeds-file ./my_feeds.txt
```

`my_feeds.txt` format (`name<TAB>rss_url`, or only `rss_url` per line):

```text
simonwillison.net	https://simonwillison.net/atom/everything/
https://example.com/rss.xml
```

## Graph Visualization

Print Mermaid source:

```bash
python /home/deming/work/news_collection/scripts/graph_viz.py --format mermaid
```

Write Mermaid to file:

```bash
python /home/deming/work/news_collection/scripts/graph_viz.py --format mermaid --out /tmp/graph.mmd
```

Write PNG (if mermaid rendering is available):

```bash
python /home/deming/work/news_collection/scripts/graph_viz.py --format png --out /tmp/graph.png
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'news_collection'`

Run from repo root and use `uv run`:

```bash
cd /home/deming/work/news_collection
uv run python -m news_collection.digest_cli --help
```

### `No matching distribution found for langgraph>=0.2.31`

You are likely on Python `<3.10` or outdated system `pip`.
Use `uv` (recommended) or upgrade Python first.

### Proxy errors like `127.0.0.1:7890 ... Operation not permitted`

Disable local proxy env vars if proxy daemon is not running:

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
```
