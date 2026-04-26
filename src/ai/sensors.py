"""Extrai 6 features normalizadas do estado do jogo para alimentar a rede NEAT."""
from src import config
from src.game.dino import Dino
from src.game.engine import GameState, _next_obstacle


def extract(dino: Dino, state: GameState) -> tuple[float, ...]:
    obs = _next_obstacle(state, dino.x)
    if obs is None:
        # nada à vista: distância máxima, resto neutro
        return (1.0, 0.0, 0.0, 0.0, state.world.speed / config.GAME_SPEED_MAX, dino.y / config.GROUND_Y)
    dist = (obs.x - (dino.x + dino.width)) / config.WINDOW_WIDTH
    width = obs.width / 80.0
    height = obs.height / 80.0
    obs_y = obs.y / config.GROUND_Y
    speed = state.world.speed / config.GAME_SPEED_MAX
    dino_y = dino.y / config.GROUND_Y
    return (dist, width, height, obs_y, speed, dino_y)


INPUT_LABELS = ["dist", "larg", "alt", "obs_y", "vel", "dino_y"]
OUTPUT_LABELS = ["PULAR", "ABAIXAR"]
