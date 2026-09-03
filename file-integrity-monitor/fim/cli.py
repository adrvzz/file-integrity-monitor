"""
cli.py

Command-line interface for the File Integrity Monitor.

Commands:
    baseline   Create a new baseline snapshot of a target directory.
    scan       Compare the current directory state against the baseline.
    watch      Monitor the directory in real time (requires 'watchdog').
"""

import argparse
import json
import sys
from pathlib import Path

from .baseline import build_baseline, save_baseline, load_baseline
from .scanner import scan_directory
from .logger_setup import setup_logger

# Directories we never want to fingerprint — version control internals,
# caches, and virtual environments change constantly and aren't part of
# the "content" being protected.
DEFAULT_EXCLUDES = [".git", "__pycache__", "node_modules", ".venv", "venv"]


def cmd_baseline(args: argparse.Namespace) -> None:
    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"Error: target directory '{target_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger(Path(args.log_dir))
    baseline = build_baseline(target_dir, algorithm=args.algorithm, exclude_dirs=DEFAULT_EXCLUDES)
    save_baseline(baseline, Path(args.baseline_file))

    logger.info(
        f"BASELINE_CREATED | target={target_dir} | files={len(baseline['files'])} | "
        f"algorithm={args.algorithm} | baseline_file={args.baseline_file}"
    )
    print(f"Baseline created: {len(baseline['files'])} file(s) tracked.")
    print(f"Saved to: {args.baseline_file}")
    if baseline["errors"]:
        print(f"Warning: {len(baseline['errors'])} file(s) could not be read and were skipped.")


def cmd_scan(args: argparse.Namespace) -> None:
    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"Error: target directory '{target_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger(Path(args.log_dir))

    try:
        baseline = load_baseline(Path(args.baseline_file))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    result = scan_directory(target_dir, baseline, exclude_dirs=DEFAULT_EXCLUDES)
    total_changes = len(result["added"]) + len(result["deleted"]) + len(result["modified"])

    print(f"\nFile Integrity Scan Report — {result['scanned_at']}")
    print(f"Target: {result['target_dir']}")
    print(f"Unchanged: {result['unchanged_count']}")
    print(f"Added:     {len(result['added'])}")
    print(f"Modified:  {len(result['modified'])}")
    print(f"Deleted:   {len(result['deleted'])}\n")

    for path in result["added"]:
        print(f"  [+] {path}")
        logger.warning(f"FILE_ADDED | {path}")

    for path in result["modified"]:
        print(f"  [~] {path}")
        logger.warning(f"FILE_MODIFIED | {path}")

    for path in result["deleted"]:
        print(f"  [-] {path}")
        logger.warning(f"FILE_DELETED | {path}")

    if total_changes == 0:
        logger.info("SCAN_CLEAN | no changes detected")
        print("No changes detected. All monitored files match the baseline.")
    else:
        logger.warning(f"SCAN_ALERT | total_changes={total_changes}")
        print(f"\n{total_changes} change(s) detected. See log for details: {Path(args.log_dir) / 'fim_events.log'}")

    if args.json:
        print("\n--- JSON OUTPUT ---")
        print(json.dumps(result, indent=2))

    # Non-zero exit on detected changes makes this scriptable in cron
    # jobs or CI pipelines (e.g. "alert if exit code != 0").
    sys.exit(1 if total_changes > 0 else 0)


def cmd_watch(args: argparse.Namespace) -> None:
    try:
        from .watcher import start_watching
    except ImportError:
        print(
            "Error: real-time watching requires the 'watchdog' package.\n"
            "Install it with: pip install watchdog",
            file=sys.stderr,
        )
        sys.exit(1)

    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"Error: target directory '{target_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger(Path(args.log_dir))
    print(f"Watching {target_dir} for real-time changes. Press Ctrl+C to stop.")
    start_watching(target_dir, logger)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fim",
        description="File Integrity Monitor — detect unauthorized file changes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_baseline = subparsers.add_parser("baseline", help="Create a new baseline snapshot")
    p_baseline.add_argument("target", help="Directory to monitor")
    p_baseline.add_argument("--baseline-file", default="baseline.json", help="Where to save the baseline (default: baseline.json)")
    p_baseline.add_argument("--algorithm", default="sha256", help="Hash algorithm to use (default: sha256)")
    p_baseline.add_argument("--log-dir", default="logs", help="Directory for log output (default: logs)")
    p_baseline.set_defaults(func=cmd_baseline)

    p_scan = subparsers.add_parser("scan", help="Scan target against the saved baseline")
    p_scan.add_argument("target", help="Directory to monitor")
    p_scan.add_argument("--baseline-file", default="baseline.json", help="Baseline file to compare against (default: baseline.json)")
    p_scan.add_argument("--log-dir", default="logs", help="Directory for log output (default: logs)")
    p_scan.add_argument("--json", action="store_true", help="Also print the full result as JSON")
    p_scan.set_defaults(func=cmd_scan)

    p_watch = subparsers.add_parser("watch", help="Monitor target in real time (requires watchdog)")
    p_watch.add_argument("target", help="Directory to monitor")
    p_watch.add_argument("--log-dir", default="logs", help="Directory for log output (default: logs)")
    p_watch.set_defaults(func=cmd_watch)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
