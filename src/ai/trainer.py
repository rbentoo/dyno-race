"""Loop NEAT: cada genoma vira um Dino; todos correm em paralelo no mesmo mundo."""
import os
import time
from typing import Optional
import neat
import pygame

from src import config, logger
from src.ai import sensors, checkpoint
from src.game.dino import Dino, color_for_index
from src.game.engine import GameState, step, render
from src.game.hud import HUD
from src.game.icon import apply as apply_icon
from src.viz.brain import BrainViz

log = logger.get(__name__)


class TrainerState:
    """Estado vivo durante uma geração — exposto pra visualização."""
    def __init__(self):
        self.generation = 0
        self.best_fitness = 0.0
        self.gen_best = 0.0
        self.current_genome = None      # melhor genoma vivo agora
        self.current_net = None
        self.current_dino: Optional[Dino] = None
        self.last_inputs: tuple = ()
        self.last_outputs: tuple = ()
        self.last_action: str = "—"


TSTATE = TrainerState()


def _eval_genomes_factory(surface: pygame.Surface, hud: HUD, brain: BrainViz, neat_config):
    def eval_genomes(genomes, _config):
        TSTATE.generation += 1
        log.info("=== geração %d iniciando | %d genomas ===", TSTATE.generation, len(genomes))
        nets = []
        ge = []
        state = GameState()
        state.dinos = []
        total = len(genomes)
        for idx, (genome_id, genome) in enumerate(genomes):
            genome.fitness = 0
            net = neat.nn.FeedForwardNetwork.create(genome, neat_config)
            nets.append(net)
            ge.append(genome)
            state.dinos.append(Dino(x=60, color=color_for_index(idx, total)))

        clock = pygame.time.Clock()
        TSTATE.gen_best = 0.0

        max_frames = 60 * 60 * 2  # 2 min por geração
        frame = 0
        while any(d.alive for d in state.dinos) and frame < max_frames:
            frame += 1
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit

            best_idx = -1
            best_fit = -1
            for i, d in enumerate(state.dinos):
                if not d.alive:
                    continue
                inputs = sensors.extract(d, state)
                out = nets[i].activate(inputs)
                if out[0] > 0.5:
                    d.jump()
                d.duck(out[1] > 0.5)
                if d.fitness > best_fit:
                    best_fit = d.fitness
                    best_idx = i
                    last_inputs, last_outputs = inputs, out

            step(state)

            if best_idx >= 0:
                d = state.dinos[best_idx]
                TSTATE.current_genome = ge[best_idx]
                TSTATE.current_net = nets[best_idx]
                TSTATE.current_dino = d
                TSTATE.last_inputs = last_inputs
                TSTATE.last_outputs = last_outputs
                if last_outputs[0] > 0.5:
                    TSTATE.last_action = "PULAR"
                elif last_outputs[1] > 0.5:
                    TSTATE.last_action = "ABAIXAR"
                else:
                    TSTATE.last_action = "CORRER"
                TSTATE.gen_best = max(TSTATE.gen_best, d.fitness)

            render(
                state, surface, hud, mode="ai",
                generation=TSTATE.generation,
                best_fitness=max(TSTATE.best_fitness, TSTATE.gen_best),
                gen_best=TSTATE.gen_best,
            )
            pygame.display.flip()
            brain.draw(TSTATE, dino_count=sum(1 for d in state.dinos if d.alive))
            clock.tick(config.FPS)

        for i, g in enumerate(ge):
            d = state.dinos[i]
            g.fitness = d.fitness + d.obstacles_passed * config.POINTS_PER_OBSTACLE
            if g.fitness > TSTATE.best_fitness:
                TSTATE.best_fitness = g.fitness

        best = max(ge, key=lambda g: g.fitness)
        checkpoint.save_best(best)
        log.info(
            "geração %d encerrada | melhor=%.1f | recorde=%.1f | nós=%d | conex=%d",
            TSTATE.generation, best.fitness, TSTATE.best_fitness,
            len(best.nodes),
            sum(1 for c in best.connections.values() if c.enabled),
        )

        _intermission(surface, brain, TSTATE)

    return eval_genomes


def _intermission(surface, brain, tstate):
    font = pygame.font.SysFont("monospace", 18, bold=True)
    big = pygame.font.SysFont("monospace", 28, bold=True)
    end = time.time() + config.AUTO_RESTART_DELAY
    clock = pygame.time.Clock()
    while time.time() < end:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit
        surface.fill((245, 245, 245))
        title = big.render(f"Geração {tstate.generation} encerrada", True, (40, 40, 40))
        surface.blit(title, title.get_rect(center=(config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2 - 40)))
        sub = font.render(
            f"melhor da geração: {tstate.gen_best:.0f}   |   recorde: {tstate.best_fitness:.0f}",
            True, (60, 60, 60),
        )
        surface.blit(sub, sub.get_rect(center=(config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)))
        secs = int(end - time.time()) + 1
        nxt = font.render(f"próxima geração em {secs}s…", True, (120, 120, 120))
        surface.blit(nxt, nxt.get_rect(center=(config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2 + 30)))
        pygame.display.flip()
        brain.draw(tstate, dino_count=0)
        clock.tick(30)


def run(resume: bool = False, generations: int = 1000):
    log.info("modo IA NEAT | resume=%s | max_geracoes=%d | pop_size=%d",
             resume, generations, config.POPULATION_SIZE)
    pygame.init()
    pygame.font.init()
    # cria a janela do cérebro ANTES da principal — assim a do jogo é a última
    # a abrir e fica com o foco no macOS/Linux/Windows.
    brain = BrainViz()
    pygame.display.set_caption("Dyno Race — IA (NEAT)")
    surface = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    apply_icon()
    hud = HUD()
    log.info("janela do cérebro: modo=%s", brain._mode)

    neat_config = neat.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config.NEAT_CONFIG_PATH,
    )

    if resume:
        seed = checkpoint.load_best()
        if seed is None:
            log.warning("ai-resume sem checkpoint em %s — iniciando do zero", config.CHECKPOINT_PATH)
            pop = neat.Population(neat_config)
        else:
            log.info("ai-resume: carregando melhor genoma salvo (fitness=%s) e seedando população",
                     getattr(seed, "fitness", "?"))
            pop = neat.Population(neat_config)
            keys = list(pop.population.keys())
            if keys:
                pop.population[keys[0]] = seed
    else:
        pop = neat.Population(neat_config)

    pop.add_reporter(neat.StdOutReporter(True))
    pop.add_reporter(neat.StatisticsReporter())

    eval_fn = _eval_genomes_factory(surface, hud, brain, neat_config)
    try:
        pop.run(eval_fn, generations)
    except SystemExit:
        log.info("treino interrompido pelo usuário")
        pygame.quit()
        raise
    pygame.quit()
    log.info("modo IA encerrado | última geração=%d | recorde=%.1f",
             TSTATE.generation, TSTATE.best_fitness)
