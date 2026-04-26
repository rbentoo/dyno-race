import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


POINTS_PER_OBSTACLE = _int("POINTS_PER_OBSTACLE", 10)
TROPHY_BASE = _int("TROPHY_BASE", 8)
POPULATION_SIZE = _int("POPULATION_SIZE", 50)
AUTO_RESTART_DELAY = _int("AUTO_RESTART_DELAY", 3)
GAME_SPEED_INITIAL = _int("GAME_SPEED_INITIAL", 6)
GAME_SPEED_MAX = _int("GAME_SPEED_MAX", 20)
WINDOW_WIDTH = _int("WINDOW_WIDTH", 1024)
WINDOW_HEIGHT = _int("WINDOW_HEIGHT", 768)
BRAIN_WINDOW_WIDTH = _int("BRAIN_WINDOW_WIDTH", 800)
BRAIN_WINDOW_HEIGHT = _int("BRAIN_WINDOW_HEIGHT", 720)
STATS_SAMPLE_INTERVAL = float(os.getenv("STATS_SAMPLE_INTERVAL", "1.0"))

FPS = 60
GROUND_Y = WINDOW_HEIGHT - 40
NEAT_CONFIG_PATH = str(Path(__file__).resolve().parent / "neat_config" / "neat-config.ini")
CHECKPOINT_PATH = str(ROOT / "checkpoints" / "best_genome.pkl")


def trophy_thresholds(max_score: int = 100_000) -> list[int]:
    """Generate trophy thresholds: TROPHY_BASE * 2^n until max."""
    thresholds = []
    n = 0
    while True:
        v = TROPHY_BASE * (2 ** n)
        if v > max_score:
            break
        thresholds.append(v)
        n += 1
    return thresholds
