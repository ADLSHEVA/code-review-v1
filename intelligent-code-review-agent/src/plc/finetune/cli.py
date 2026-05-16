"""CLI for generating PLC fine-tuning datasets.

Usage:
    python -m src.plc.finetune.cli [OPTIONS]

Examples:
    # Generate from rules + vulnerability DB only
    python -m src.plc.finetune.cli --output ./data/training.jsonl

    # Generate from a codebase
    python -m src.plc.finetune.cli --repo /path/to/plc/project --output ./data/training.jsonl

    # Export in Alpaca format
    python -m src.plc.finetune.cli --format alpaca --output ./data/training.json

    # Generate with train/val/test split
    python -m src.plc.finetune.cli --split --output-dir ./data/
"""

import argparse
import sys
from pathlib import Path

from .dataset_generator import DatasetGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate fine-tuning datasets for PLC code review LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="Path to PLC codebase to scan for training examples",
    )
    parser.add_argument(
        "--output", "-o", type=str, default="./data/plc_finetune.jsonl",
        help="Output file path (default: ./data/plc_finetune.jsonl)",
    )
    parser.add_argument(
        "--format", "-f", type=str, default="jsonl",
        choices=["jsonl", "alpaca", "sharegpt"],
        help="Output format (default: jsonl)",
    )
    parser.add_argument(
        "--split", action="store_true",
        help="Split into train/val/test sets",
    )
    parser.add_argument(
        "--output-dir", type=str, default="./data/",
        help="Output directory for split files",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8,
        help="Train set ratio (default: 0.8)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print dataset statistics",
    )

    args = parser.parse_args()

    generator = DatasetGenerator()
    print("Generating training examples...", file=sys.stderr)

    examples = generator.generate_all(repo_path=args.repo)
    print(f"Generated {len(examples)} examples", file=sys.stderr)

    if args.stats:
        stats = generator.get_stats(examples)
        print(f"\nDataset Statistics:", file=sys.stderr)
        print(f"  Total: {stats.total_examples}", file=sys.stderr)
        print(f"  By severity: {stats.by_severity}", file=sys.stderr)
        print(f"  By source: {stats.by_source}", file=sys.stderr)

    if args.split:
        train, val, test = generator.split_dataset(
            examples, args.train_ratio, seed=args.seed
        )
        out_dir = Path(args.output_dir)
        ext = {"jsonl": ".jsonl", "alpaca": ".json", "sharegpt": ".json"}[args.format]

        for name, data in [("train", train), ("val", val), ("test", test)]:
            out_path = str(out_dir / f"{name}{ext}")
            if args.format == "jsonl":
                generator.export_jsonl(data, out_path)
            elif args.format == "alpaca":
                generator.export_alpaca(data, out_path)
            else:
                generator.export_sharegpt(data, out_path)
            print(f"  {name}: {len(data)} examples → {out_path}", file=sys.stderr)
    else:
        if args.format == "jsonl":
            generator.export_jsonl(examples, args.output)
        elif args.format == "alpaca":
            generator.export_alpaca(examples, args.output)
        else:
            generator.export_sharegpt(examples, args.output)
        print(f"Exported to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
