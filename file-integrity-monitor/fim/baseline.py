"""
baseline.py

Builds, saves, and loads the integrity baseline: a JSON snapshot of
every monitored file's hash, size, and last-modified time at the
moment the baseline was captured. Later scans compare the live
filesystem state against this snapshot to detect drift.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .hasher import hash_file

DEFAULT_ALGORITHM = "sha256"


def build_baseline(target_dir: Path, algorithm: str = DEFAULT_ALGORITHM, exclude_dirs=None) -> dict:
    """
    Walk target_dir and build a baseline dict of file metadata.

    Files that can't be read (permission errors, broken symlinks,
    etc.) are skipped and recorded under "errors" rather than
    crashing the whole run.
    """
    exclude_dirs = set(exclude_dirs or [])
    files_data = {}
    errors = []

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            full_path = Path(root) / name
            rel_path = str(full_path.relative_to(target_dir))
            try:
                stat = full_path.stat()
                files_data[rel_path] = {
                    "hash": hash_file(full_path, algorithm),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                }
            except (PermissionError, FileNotFoundError, OSError) as e:
                errors.append({"path": rel_path, "error": str(e)})

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_dir": str(target_dir.resolve()),
        "algorithm": algorithm,
        "files": files_data,
        "errors": errors,
    }


def save_baseline(baseline: dict, output_path: Path) -> None:
    """Write a baseline dict to disk as pretty-printed JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)


def load_baseline(baseline_path: Path) -> dict:
    """Load a previously saved baseline JSON file."""
    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Baseline file not found at {baseline_path}. "
            "Run 'python run_fim.py baseline <target_dir>' first to create one."
        )
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)
