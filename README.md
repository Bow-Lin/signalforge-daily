# News Collection (LangGraph)

Collect topic-related content with LangGraph. Currently implements paper collection via arXiv.
Uses a two-step LLM plan-and-select flow with sequential tool execution and PDF evidence.

## Setup

1) Install dependencies:

```bash
pip install -r requirements.txt
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
