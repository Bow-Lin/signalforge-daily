from __future__ import annotations

import argparse

from signalforge_daily.graph import build_graph


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize LangGraph.")
    parser.add_argument("--format", choices=["png", "mermaid"], default="mermaid")
    parser.add_argument("--out", help="Output file path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    graph = build_graph().compile()
    g = graph.get_graph()

    if args.format == "png":
        data = g.draw_mermaid_png()
        if args.out:
            with open(args.out, "wb") as f:
                f.write(data)
        else:
            print(data)
    else:
        mermaid = g.draw_mermaid()
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(mermaid)
        else:
            print(mermaid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
