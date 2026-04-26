"""Engine reutilizável: roda 1 partida (humano) ou N dinos em paralelo (NEAT)."""
from dataclasses import dataclass, field
from typing import Callable, Optional
import pygame
from src import config, logger
from src.game.dino import Dino
from src.game.obstacles import Spawner
from src.game.world import World
from src.game.hud import HUD
from src.game.icon import apply as apply_icon

log = logger.get(__name__)


@dataclass
class GameState:
    world: World = field(default_factory=World)
    dinos: list[Dino] = field(default_factory=list)
    obstacles: list = field(default_factory=list)
    spawner: Spawner = field(default_factory=Spawner)
    score: int = 0  # usado em modo humano

    def reset(self):
        self.world.reset()
        self.obstacles.clear()
        self.spawner.reset()
        self.score = 0
        for d in self.dinos:
            d.fitness = 0
            d.obstacles_passed = 0
            d.alive = True
            d.color = (60, 60, 60)
            d.y = config.GROUND_Y - d.height
            d.vy = 0
            d.on_ground = True


def _next_obstacle(state: GameState, dino_x: float):
    for o in state.obstacles:
        if o.x + o.width >= dino_x:
            return o
    return None


def step(state: GameState, on_dino_pass: Optional[Callable] = None):
    """Avança 1 frame. Atualiza mundo, obstáculos, colisões."""
    state.world.update()
    state.spawner.update(
        state.obstacles,
        state.world.speed,
        allow_birds=state.world.distance > 3000,
    )

    for o in state.obstacles:
        o.update(state.world.speed)

    remaining = []
    for o in state.obstacles:
        if o.x + o.width < 0:
            for d in state.dinos:
                if d.alive and not o.passed:
                    d.obstacles_passed += 1
            if not o.passed:
                state.score += config.POINTS_PER_OBSTACLE
                if on_dino_pass:
                    on_dino_pass()
            o.passed = True
        else:
            remaining.append(o)
    state.obstacles = remaining

    # update sempre (mesmo morto) pra animação de morte avançar
    for d in state.dinos:
        d.update()
        if not d.alive:
            continue
        d.fitness += 1
        for o in state.obstacles:
            if d.rect.colliderect(o.rect):
                d.kill()
                break


def render(state: GameState, surface: pygame.Surface, hud: HUD, *, mode: str,
           generation: int = 0, best_fitness: float = 0, gen_best: float = 0,
           elapsed_seconds: float = 0.0):
    state.world.draw(surface)
    for o in state.obstacles:
        o.draw(surface)
    # mortos primeiro (fantasma) pra não cobrir os vivos
    for d in state.dinos:
        if not d.alive:
            d.draw(surface, ghost=(mode == "ai"))
    for d in state.dinos:
        if d.alive:
            d.draw(surface, ghost=False)
    if mode == "human":
        d = state.dinos[0]
        hud.draw_human(
            surface, score=state.score,
            km=state.world.km, seconds=state.world.seconds,
            speed=state.world.speed, speed_max=config.GAME_SPEED_MAX,
            dead=not d.alive,
        )
    else:
        alive = sum(1 for d in state.dinos if d.alive)
        hud.draw_ai(
            surface, generation=generation, alive=alive, total=len(state.dinos),
            best_fitness=best_fitness, gen_best=gen_best, km=state.world.km,
            speed=state.world.speed, speed_max=config.GAME_SPEED_MAX,
            elapsed_seconds=elapsed_seconds,
        )


def run_human():
    log.info("modo humano: %dx%d @ %d FPS", config.WINDOW_WIDTH, config.WINDOW_HEIGHT, config.FPS)
    pygame.init()
    pygame.display.set_caption("Dyno Race — Humano")
    surface = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    apply_icon()
    clock = pygame.time.Clock()
    hud = HUD()
    state = GameState()
    state.dinos = [Dino()]
    runs = 1
    last_dead = False
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_UP):
                    if state.dinos[0].alive:
                        state.dinos[0].jump()
                    else:
                        runs += 1
                        log.info("reiniciando partida #%d", runs)
                        state.reset()
                        last_dead = False
                elif ev.key == pygame.K_ESCAPE:
                    running = False
        keys = pygame.key.get_pressed()
        state.dinos[0].duck(keys[pygame.K_DOWN])

        if state.dinos[0].alive:
            step(state)
        elif not last_dead:
            last_dead = True
            log.info(
                "game over | partida=%d | pontos=%d | km=%.2f | tempo=%.1fs",
                runs, state.score, state.world.km, state.world.seconds,
            )
        render(state, surface, hud, mode="human")
        pygame.display.flip()
        clock.tick(config.FPS)
    pygame.quit()
    log.info("modo humano encerrado após %d partida(s)", runs)
