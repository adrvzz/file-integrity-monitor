"""
test_fim.py

Unit tests for the File Integrity Monitor core logic (hashing,
baselining, and scanning). These don't touch the CLI layer directly —
they test the functions the CLI calls.

Run with:
    pytest tests/ -v
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from fim.baseline import build_baseline, save_baseline, load_baseline
from fim.hasher import hash_file
from fim.scanner import scan_directory


@pytest.fixture
def temp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_hash_file_is_deterministic(temp_dir):
    f = temp_dir / "sample.txt"
    f.write_text("hello world")
    assert hash_file(f) == hash_file(f)


def test_hash_file_changes_with_content(temp_dir):
    f = temp_dir / "sample.txt"
    f.write_text("hello world")
    h1 = hash_file(f)
    f.write_text("hello world!")
    h2 = hash_file(f)
    assert h1 != h2


def test_build_baseline_tracks_all_files(temp_dir):
    (temp_dir / "a.txt").write_text("aaa")
    (temp_dir / "b.txt").write_text("bbb")
    baseline = build_baseline(temp_dir)
    assert set(baseline["files"].keys()) == {"a.txt", "b.txt"}
    assert baseline["algorithm"] == "sha256"
    assert baseline["errors"] == []


def test_build_baseline_walks_subdirectories(temp_dir):
    (temp_dir / "sub").mkdir()
    (temp_dir / "sub" / "nested.txt").write_text("nested")
    baseline = build_baseline(temp_dir)
    assert "sub/nested.txt" in baseline["files"]


def test_build_baseline_respects_exclude_dirs(temp_dir):
    (temp_dir / "a.txt").write_text("aaa")
    (temp_dir / ".git").mkdir()
    (temp_dir / ".git" / "config").write_text("ignored")
    baseline = build_baseline(temp_dir, exclude_dirs=[".git"])
    assert set(baseline["files"].keys()) == {"a.txt"}


def test_scan_detects_no_changes(temp_dir):
    (temp_dir / "a.txt").write_text("aaa")
    baseline = build_baseline(temp_dir)
    result = scan_directory(temp_dir, baseline)
    assert result["added"] == []
    assert result["deleted"] == []
    assert result["modified"] == []
    assert result["unchanged_count"] == 1


def test_scan_detects_modified_file(temp_dir):
    f = temp_dir / "a.txt"
    f.write_text("aaa")
    baseline = build_baseline(temp_dir)
    f.write_text("changed content")
    result = scan_directory(temp_dir, baseline)
    assert result["modified"] == ["a.txt"]
    assert result["unchanged_count"] == 0


def test_scan_detects_added_file(temp_dir):
    (temp_dir / "a.txt").write_text("aaa")
    baseline = build_baseline(temp_dir)
    (temp_dir / "b.txt").write_text("bbb")
    result = scan_directory(temp_dir, baseline)
    assert result["added"] == ["b.txt"]


def test_scan_detects_deleted_file(temp_dir):
    a = temp_dir / "a.txt"
    a.write_text("aaa")
    (temp_dir / "b.txt").write_text("bbb")
    baseline = build_baseline(temp_dir)
    a.unlink()
    result = scan_directory(temp_dir, baseline)
    assert result["deleted"] == ["a.txt"]


def test_scan_handles_simultaneous_changes(temp_dir):
    (temp_dir / "keep.txt").write_text("same")
    (temp_dir / "edit.txt").write_text("before")
    (temp_dir / "remove.txt").write_text("bye")
    baseline = build_baseline(temp_dir)

    (temp_dir / "edit.txt").write_text("after")
    (temp_dir / "remove.txt").unlink()
    (temp_dir / "new.txt").write_text("new")

    result = scan_directory(temp_dir, baseline)
    assert result["added"] == ["new.txt"]
    assert result["deleted"] == ["remove.txt"]
    assert result["modified"] == ["edit.txt"]
    assert result["unchanged_count"] == 1


def test_save_and_load_baseline_roundtrip(temp_dir):
    (temp_dir / "a.txt").write_text("aaa")
    baseline = build_baseline(temp_dir)
    baseline_file = temp_dir / "baseline.json"
    save_baseline(baseline, baseline_file)
    loaded = load_baseline(baseline_file)
    assert loaded["files"] == baseline["files"]


def test_load_missing_baseline_raises(temp_dir):
    with pytest.raises(FileNotFoundError):
        load_baseline(temp_dir / "does_not_exist.json")
