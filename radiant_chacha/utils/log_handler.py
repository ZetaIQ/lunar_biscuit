import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Centralized logger factory used across the project.
# Usage: from radiant_chacha.utils.log_handler import get_logger
#        logger = get_logger(__name__, source_file=__file__)
#
# Creates two handlers:
#  - StreamHandler to stdout
#  - FileHandler to logs/app/... or logs/tests/... depending on source_file path
#
# File naming: <YYYY-MM-DD>-<file-name>.log placed under logs/app or logs/tests (UTC date)
# Global log level (configurable)
from radiant_chacha.config import LOG_LEVEL


def set_log_level(level: int) -> None:
    """Update global log level for all future loggers."""
    global LOG_LEVEL
    LOG_LEVEL = level


def _ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def get_logger(
    name: str,
    *,
    source_file: Optional[str] = None,
    for_tests: Optional[bool] = None,
    level: Optional[int] = None,
) -> logging.Logger:
    """
    Return a configured logger writing to stdout and a per-module file.

    Parameters
    ----------
    name : str
        Logger name (typically __name__).
    source_file : str, optional
        Path to source file; used to craft logfile name and infer test vs app.
        If None, name is used for the logfile.
    for_tests : bool, optional
        Force test vs app mode. If None, inferred from source_file path.
    level : int, optional
        Log level (default: use global LOG_LEVEL).

    Returns
    -------
    logging.Logger
        Configured logger with StreamHandler and FileHandler.
    """
    if level is None:
        level = LOG_LEVEL

    logger = logging.getLogger(name)

    # Avoid reconfiguring if already set up
    if len(logger.handlers) > 0:
        logger.setLevel(level)
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Stream handler (stdout)
    sh = logging.StreamHandler()
    sh.setLevel(level)
    formatter = logging.Formatter("%(asctime)sZ %(levelname)-8s %(name)s: %(message)s")
    # Use UTC timestamps
    formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # Determine logfile path
    # Project root (two levels up from this file): lunar_biscuit/
    project_root = Path(__file__).resolve().parents[2]
    logs_root = project_root / "logs"
    inferred_tests = False
    file_basename = (
        Path(source_file).name if source_file else (name.replace(".", "_") + ".log")
    )

    if for_tests is None and source_file:
        if "radiant_chacha/tests" in str(Path(source_file).as_posix()):
            inferred_tests = True
    elif for_tests is True:
        inferred_tests = True

    subdir = "tests" if inferred_tests else "app"
    logs_dir = logs_root / subdir
    _ensure_dir(logs_dir)

    # Use date-only filename so logs append per day (UTC date)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logfile = logs_dir / f"{date_str}-{file_basename.replace('.', '_')}.log"

    # FileHandler defaults to append mode, but set explicitly for clarity
    fh = logging.FileHandler(logfile, mode="a", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger
