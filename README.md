# News Collection (LangGraph)

Collect topic-related content with LangGraph. Currently implements paper collection via arXiv.
Uses LangGraph's tool calling to let an LLM decide which papers are valuable after reading PDFs.

## Usage

1) Install dependencies:

```bash
pip install -r requirements.txt
```

2) Run:

```bash
python -m news_collection.cli \
  --topic "RTL 代码生成 且使用cvdp数据集或RealBench数据集" \
  --content-type paper \
  --start "2025-09-01" \
  --end "2026-01-15" \
  --tz "Asia/Shanghai" \
  --iflow-model "qwen3-max" \
  --max-results 5 \
  --pdf-max-chars 16000
```

Collected items are saved under `/home/deming/work/collection/paper/papers_latest.jsonl`.
Downloaded PDFs are cached under `/home/deming/work/collection/paper/pdf_cache/`.
