"""
hasher.py

Utility functions for computing cryptographic hashes of files.

We hash files in fixed-size chunks rather than reading them all at
once so that large files don't get fully loaded into memory.
"""

import hashlib
from pathlib import Path

CHUNK_SIZE = 65536  # 64 KB per read


def hash_file(filepath: Path, algorithm: str = "sha256") -> str:
    """
    Compute the hex digest of a file's contents.

    Args:
        filepath: Path to the file to hash.
        algorithm: Any algorithm name supported by hashlib
            (e.g. "sha256", "sha1", "md5"). sha256 is the default
            because it has no known practical collision attacks,
            unlike md5 or sha1.

    Returns:
        The hex digest string of the file's hash.

    Raises:
        FileNotFoundError: If filepath does not exist.
        PermissionError: If the file cannot be read.
        OSError: For other I/O failures (e.g. broken symlinks).
    """
    hash_obj = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
