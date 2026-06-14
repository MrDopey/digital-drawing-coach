from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    from dotenv import load_dotenv

    from drawing_coach import env
    from drawing_coach.paths import config_path

    load_dotenv(dotenv_path=config_path().parent / ".env", override=False)

    raw_level = env.log_level().upper()
    if raw_level and raw_level not in _VALID_LEVELS:
        print(
            f'Unknown log level "{raw_level}", defaulting to WARNING', file=sys.stderr
        )
        raw_level = "WARNING"
    level = getattr(logging, raw_level or "WARNING")

    raw_max = env.log_max_bytes()
    max_bytes = _DEFAULT_MAX_BYTES
    if raw_max:
        try:
            parsed = int(raw_max)
            if parsed <= 0:
                raise ValueError("must be positive")
            max_bytes = parsed
        except (ValueError, OverflowError):
            print(
                f'Invalid DRAWING_COACH_LOG_MAX_BYTES "{raw_max}",'
                f" defaulting to {_DEFAULT_MAX_BYTES}",
                file=sys.stderr,
            )

    root = logging.getLogger("drawing_coach")
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_dest: str = "none"
    log_file = env.log_file()
    if log_file:
        p = Path(log_file)
        if not p.parent.exists():
            print(
                f"Cannot write log file at {log_file}: parent directory does not exist",
                file=sys.stderr,
            )
        else:
            try:
                fh = RotatingFileHandler(str(p), maxBytes=max_bytes, backupCount=0)
                fh.setFormatter(formatter)
                root.addHandler(fh)
                file_dest = str(p)
            except OSError as exc:
                print(f"Cannot write log file at {log_file}: {exc}", file=sys.stderr)

    root.debug("Log level=%s file=%s", raw_level or "WARNING", file_dest)
