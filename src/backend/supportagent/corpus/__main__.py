"""CLI: generate the corpus and its gold evaluation set to local files.

    python -m supportagent.corpus                     # write to data/corpus/
    python -m supportagent.corpus --stats-only        # inspect without writing

Generation is local by design. Publishing into the real Confluence space is a
separate, explicit step - creating hundreds of pages in a live tenant should not
be a side effect of running a generator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evalgen import category_counts, generate_gold_set
from .generate import generate
from .world import WORLD_MODEL_PATH, load_world

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "corpus"
DEFAULT_EVAL_PATH = PROJECT_ROOT / "evals" / "rag_qa.generated.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="supportagent.corpus")
    parser.add_argument("--world", type=Path, default=WORLD_MODEL_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument(
        "--jira-patterns-per-variant",
        type=int,
        default=1,
        help="distractor issues generated per fact variant (raises Jira volume)",
    )
    parser.add_argument("--noise-issues", type=int, default=12)
    parser.add_argument("--stats-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    world = load_world(args.world)
    corpus = generate(
        world,
        jira_patterns_per_variant=args.jira_patterns_per_variant,
        noise_issues=args.noise_issues,
    )
    gold = generate_gold_set(world, corpus)

    print("corpus:", json.dumps(corpus.stats(), indent=2))
    print(f"gold cases: {len(gold)}")
    print("by category:", json.dumps(category_counts(gold), indent=2))

    if args.stats_only:
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.out_dir / "projects.json", corpus.projects)
    _write_json(args.out_dir / "confluence_pages.json", corpus.pages)
    _write_json(args.out_dir / "jira_issues.json", corpus.issues)

    args.eval_out.parent.mkdir(parents=True, exist_ok=True)
    args.eval_out.write_text(
        "\n".join(json.dumps(case.to_dict(), ensure_ascii=False) for case in gold) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote corpus to {args.out_dir}")
    print(f"wrote gold set to {args.eval_out}")


def _write_json(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
