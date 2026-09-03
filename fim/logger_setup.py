"""
logger_setup.py

Configures a logger that writes structured, timestamped log lines to
both the console and a log file. The log format is deliberately
simple and greppable (pipe-delimited key=value style) so it can be
fed into a log parser later — see the Log Analyzer project later in
this portfolio, which is designed to ingest logs in this same shape.
"""

import logging
from pathlib import Path


def setup_logger(log_dir: Path, name: str = "fim", level: int = logging.INFO) -> logging.Logger:
    """
    Create (or fetch) a logger that writes to <log_dir>/fim_events.log
    and to stdout.

    Calling this more than once with the same `name` returns the same
    logger without attaching duplicate handlers (a common source of
    doubled-up log lines in Python logging).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "fim_events.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    fmt = "%(asctime)s | %(levelname)-8s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S%z")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
