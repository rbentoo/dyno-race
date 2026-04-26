"""Logging centralizado: console colorido + arquivo rotativo em logs/."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "dyno-race.log"

LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
FMT = "%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"

_COLORS = {
    "DEBUG": "\033[36m",     # ciano
    "INFO": "\033[32m",      # verde
    "WARNING": "\033[33m",   # amarelo
    "ERROR": "\033[31m",     # vermelho
    "CRITICAL": "\033[1;31m",
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        if sys.stdout.isatty():
            color = _COLORS.get(record.levelname, "")
            return f"{color}{msg}{_RESET}"
        return msg


_initialized = False


def setup() -> None:
    """Idempotente: configura handlers uma única vez."""
    global _initialized
    if _initialized:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("dyno")
    root.setLevel(LEVEL)
    root.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(_ColorFormatter(FMT, datefmt=DATEFMT))
    root.addHandler(console)

    file_h = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    file_h.setFormatter(logging.Formatter(FMT, datefmt=DATEFMT))
    root.addHandler(file_h)

    _initialized = True


def get(name: str) -> logging.Logger:
    """Use: log = logger.get(__name__)."""
    setup()
    short = name.replace("src.", "")
    return logging.getLogger(f"dyno.{short}")
