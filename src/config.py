import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _opt_float(name: str) -> float | None:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else None


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
# Tempo máximo (segundos) que uma geração pode durar. 0 = sem limite (corre até
# todos os dinos morrerem, mesmo que demore horas).
MAX_GENERATION_SECONDS = _int("MAX_GENERATION_SECONDS", 0)
# Frames mínimos entre obstáculos (teto de dificuldade do jogo). Quanto menor,
# mais apertado fica em alta velocidade. Default 40 = ~0.67s a 60fps.
OBSTACLE_MIN_GAP_FRAMES = _int("OBSTACLE_MIN_GAP_FRAMES", 40)
# Guardrail: encerra a geração se o jogo ficar travado em GAME_SPEED_MAX por
# este tempo (segundos). Quando saturou, a run não tem mais o que mostrar —
# salva os dados e segue. 0 = desligado. Default 900 = 15 min.
MAX_SECONDS_AT_TOP_SPEED = _int("MAX_SECONDS_AT_TOP_SPEED", 900)
# Limite de gerações por run. 0 = ilimitado (encerra só por fitness_threshold,
# extinção ou Ctrl+C). Default 1000.
MAX_GENERATIONS = _int("MAX_GENERATIONS", 1000)

# Overrides opcionais do NEAT (vêm do .env > seção avançada).
# None = mantém o valor de src/neat_config/neat-config.ini.
# Cada chave é (caminho de atributo no objeto neat.Config, env var).
NEAT_OVERRIDES: dict[str, float | None] = {
    "species_set_config.compatibility_threshold": _opt_float("NEAT_COMPATIBILITY_THRESHOLD"),
    "stagnation_config.max_stagnation": _opt_float("NEAT_MAX_STAGNATION"),
    "stagnation_config.species_elitism": _opt_float("NEAT_SPECIES_ELITISM"),
    "reproduction_config.elitism": _opt_float("NEAT_ELITISM"),
    "reproduction_config.survival_threshold": _opt_float("NEAT_SURVIVAL_THRESHOLD"),
    "genome_config.node_add_prob": _opt_float("NEAT_NODE_ADD_PROB"),
    "genome_config.node_delete_prob": _opt_float("NEAT_NODE_DELETE_PROB"),
    "genome_config.conn_add_prob": _opt_float("NEAT_CONN_ADD_PROB"),
    "genome_config.conn_delete_prob": _opt_float("NEAT_CONN_DELETE_PROB"),
    "genome_config.weight_mutate_rate": _opt_float("NEAT_WEIGHT_MUTATE_RATE"),
    "genome_config.weight_mutate_power": _opt_float("NEAT_WEIGHT_MUTATE_POWER"),
}

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
