"""
watcher.py

Optional real-time monitoring mode built on top of the 'watchdog'
library. This is a bonus mode on top of the core baseline/scan
workflow: instead of polling on demand, it reacts to OS-level
filesystem events as they happen.

Requires: pip install watchdog
"""

import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class IntegrityEventHandler(FileSystemEventHandler):
    """Logs every real-time filesystem event under the watched path."""

    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    def on_created(self, event):
        if not event.is_directory:
            self.logger.warning(f"FILE_ADDED (real-time) | {event.src_path}")
            print(f"  [+] Created: {event.src_path}")

    def on_deleted(self, event):
        if not event.is_directory:
            self.logger.warning(f"FILE_DELETED (real-time) | {event.src_path}")
            print(f"  [-] Deleted: {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            self.logger.warning(f"FILE_MODIFIED (real-time) | {event.src_path}")
            print(f"  [~] Modified: {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory:
            self.logger.warning(f"FILE_MOVED (real-time) | {event.src_path} -> {event.dest_path}")
            print(f"  [->] Moved: {event.src_path} -> {event.dest_path}")


def start_watching(target_dir: Path, logger) -> None:
    """Block and watch target_dir until interrupted with Ctrl+C."""
    handler = IntegrityEventHandler(logger)
    observer = Observer()
    observer.schedule(handler, str(target_dir), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching.")
    observer.join()
