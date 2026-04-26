import os
import pickle
from pathlib import Path
from src import config, logger

log = logger.get(__name__)


def save_best(genome) -> None:
    Path(config.CHECKPOINT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(config.CHECKPOINT_PATH, "wb") as f:
        pickle.dump(genome, f)
    log.debug("checkpoint salvo em %s (fitness=%.1f)", config.CHECKPOINT_PATH, genome.fitness or 0)


def load_best():
    if not os.path.exists(config.CHECKPOINT_PATH):
        log.debug("nenhum checkpoint em %s", config.CHECKPOINT_PATH)
        return None
    with open(config.CHECKPOINT_PATH, "rb") as f:
        g = pickle.load(f)
    log.info("checkpoint carregado de %s", config.CHECKPOINT_PATH)
    return g
