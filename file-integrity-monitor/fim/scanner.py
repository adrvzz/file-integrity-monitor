"""
scanner.py

Compares the current state of a directory against a saved baseline
and classifies every file as unchanged, modified, added, or deleted.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from .hasher import hash_file


def scan_directory(target_dir: Path, baseline: dict, exclude_dirs=None) -> dict:
    """
    Walk target_dir, compare it against `baseline`, and return a
    report dict describing what changed.
    """
    algorithm = baseline.get("algorithm", "sha256")
    exclude_dirs = set(exclude_dirs or [])
    baseline_files = baseline.get("files", {})

    current_files = {}
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            full_path = Path(root) / name
            rel_path = str(full_path.relative_to(target_dir))
            current_files[rel_path] = full_path

    baseline_paths = set(baseline_files.keys())
    current_paths = set(current_files.keys())

    added = sorted(current_paths - baseline_paths)
    deleted = sorted(baseline_paths - current_paths)
    common = current_paths & baseline_paths

    modified = []
    unchanged = []

    for rel_path in sorted(common):
        try:
            current_hash = hash_file(current_files[rel_path], algorithm)
        except (PermissionError, FileNotFoundError, OSError):
            # A file that suddenly can't be read is itself suspicious —
            # treat it as a change rather than silently skipping it.
            modified.append(rel_path)
            continue

        if current_hash != baseline_files[rel_path]["hash"]:
            modified.append(rel_path)
        else:
            unchanged.append(rel_path)

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "target_dir": str(target_dir.resolve()),
        "added": added,
        "deleted": deleted,
        "modified": modified,
        "unchanged_count": len(unchanged),
    }
