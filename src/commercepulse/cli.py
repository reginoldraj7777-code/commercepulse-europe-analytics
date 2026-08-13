from __future__ import annotations

import argparse
import json
from pathlib import Path

from commercepulse.analysis import run_analysis
from commercepulse.config import load_profile
from commercepulse.generator import generate_scenario
from commercepulse.postgres import load_clean_folder
from commercepulse.quality import run_quality_pipeline


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commercepulse",
        description="Generate, validate, analyze, and load the CommercePulse Europe scenario.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate deterministic raw scenario data")
    generate.add_argument("--profile", choices=["ci", "portfolio"], default="ci")
    generate.add_argument("--output", type=Path, default=Path("data/sample"))

    quality = subparsers.add_parser("quality", help="Clean, quarantine, and validate raw data")
    quality.add_argument("--input", type=Path, default=Path("data/sample"))
    quality.add_argument("--output", type=Path, default=Path("artifacts/validation"))

    analyze = subparsers.add_parser("analyze", help="Build decision-ready analytical outputs")
    analyze.add_argument("--input", type=Path, default=Path("data/sample/clean"))
    analyze.add_argument("--output", type=Path, default=Path("artifacts/analysis"))

    load = subparsers.add_parser("load-postgres", help="Load clean Parquet tables into raw schema")
    load.add_argument("--input", type=Path, default=Path("data/sample/clean"))

    all_command = subparsers.add_parser("all", help="Generate, validate, and analyze")
    all_command.add_argument("--profile", choices=["ci", "portfolio"], default="ci")
    all_command.add_argument("--data-root", type=Path, default=Path("data/sample"))
    all_command.add_argument("--artifact-root", type=Path, default=Path("artifacts"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "generate":
        result = generate_scenario(load_profile(args.profile), args.output)
    elif args.command == "quality":
        result = run_quality_pipeline(args.input, args.output)
    elif args.command == "analyze":
        result = run_analysis(args.input, args.output)
    elif args.command == "load-postgres":
        result = {"loaded": load_clean_folder(args.input)}
    elif args.command == "all":
        generation = generate_scenario(load_profile(args.profile), args.data_root)
        quality = run_quality_pipeline(args.data_root, args.artifact_root / "validation")
        analysis = run_analysis(args.data_root / "clean", args.artifact_root / "analysis")
        result = {
            "generation_rows": generation["total_rows"],
            "quality_status": quality["status"],
            "analysis_reconciliation": analysis["reconciliation_status"],
        }
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
