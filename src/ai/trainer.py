"""Loop NEAT: cada genoma vira um Dino; todos correm em paralelo no mesmo mundo."""
import csv
import re
import time
from datetime import datetime
from statistics import mean, stdev
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
        self.started_at = time.monotonic()
        self.generation = 0
        self.best_fitness = 0.0
        self.gen_best = 0.0
        self.current_genome = None      # melhor genoma vivo agora
        self.current_net = None
        self.current_dino: Optional[Dino] = None
        self.last_inputs: tuple = ()
        self.last_outputs: tuple = ()
        self.last_action: str = "—"
        self.last_generation_metrics: dict = {}
        self.run_id: str = ""           # mesmo run_id usado no CSV (pra cruzar com o dashboard)
        self.current_species_id: Optional[int] = None


TSTATE = TrainerState()


class ExperimentReporter(neat.reporting.BaseReporter):
    """Salva um CSV incremental com uma linha por geração concluída."""

    # Defaults usados pra preencher colunas ausentes ao migrar CSVs antigos.
    LEGACY_DEFAULTS = {
        "obstacle_min_gap_frames": "40",
    }

    FIELDNAMES = [
        "run_id", "generation", "elapsed_seconds", "generation_time_seconds",
        "population_size", "game_speed_initial", "game_speed_max",
        "points_per_obstacle", "auto_restart_delay", "obstacle_min_gap_frames",
        "resume", "compatibility_threshold", "max_stagnation", "species_elitism",
        "elitism", "survival_threshold", "node_add_prob", "node_delete_prob",
        "conn_add_prob", "conn_delete_prob", "weight_mutate_rate", "weight_mutate_power",
        "best_fitness_generation", "best_fitness_run", "avg_fitness", "stdev_fitness",
        "best_genome_id", "best_species_id", "best_nodes", "best_connections",
        "best_enabled_connections", "best_obstacles_passed", "best_km", "best_speed_reached",
        "species_count", "species_sizes", "max_species_stagnation",
        "mean_genetic_distance", "genetic_distance_stdev",
    ]

    def __init__(self, tstate: TrainerState, neat_config, resume: bool):
        self.tstate = tstate
        self.neat_config = neat_config
        self.resume = resume
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = config.ROOT / "results" / "dyno-race.csv"
        self.file = None
        self.writer = None
        self.generation = 0
        self.generation_started_at = time.monotonic()
        self.row: dict = {}
        log.info("relatório CSV do experimento será anexado em: %s (run_id=%s)", self.path, self.run_id)

    def _ensure_open(self):
        if self.file is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_schema_if_needed()
        write_header = not self.path.exists() or self.path.stat().st_size == 0
        self.file = self.path.open("a", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.FIELDNAMES)
        if write_header:
            self.writer.writeheader()

    def _migrate_schema_if_needed(self):
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            old_fieldnames = reader.fieldnames or []
            if old_fieldnames == self.FIELDNAMES:
                return
            rows = list(reader)
        with self.path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    name: row.get(name) if row.get(name) not in (None, "")
                    else self.LEGACY_DEFAULTS.get(name, "")
                    for name in self.FIELDNAMES
                })

    def start_generation(self, generation):
        self.generation = generation
        self.generation_started_at = time.monotonic()
        self.row = {
            "run_id": self.run_id,
            "generation": generation + 1,
            "population_size": config.POPULATION_SIZE,
            "game_speed_initial": config.GAME_SPEED_INITIAL,
            "game_speed_max": config.GAME_SPEED_MAX,
            "points_per_obstacle": config.POINTS_PER_OBSTACLE,
            "auto_restart_delay": config.AUTO_RESTART_DELAY,
            "obstacle_min_gap_frames": config.OBSTACLE_MIN_GAP_FRAMES,
            "resume": int(self.resume),
            "compatibility_threshold": self.neat_config.species_set_config.compatibility_threshold,
            "max_stagnation": self.neat_config.stagnation_config.max_stagnation,
            "species_elitism": self.neat_config.stagnation_config.species_elitism,
            "elitism": self.neat_config.reproduction_config.elitism,
            "survival_threshold": self.neat_config.reproduction_config.survival_threshold,
            "node_add_prob": self.neat_config.genome_config.node_add_prob,
            "node_delete_prob": self.neat_config.genome_config.node_delete_prob,
            "conn_add_prob": self.neat_config.genome_config.conn_add_prob,
            "conn_delete_prob": self.neat_config.genome_config.conn_delete_prob,
            "weight_mutate_rate": self.neat_config.genome_config.weight_mutate_rate,
            "weight_mutate_power": self.neat_config.genome_config.weight_mutate_power,
        }

    def post_evaluate(self, _config, population, species, best_genome):
        fitnesses = [g.fitness or 0.0 for g in population.values()]
        species_id = species.get_species_id(best_genome.key)
        enabled_connections = sum(1 for c in best_genome.connections.values() if c.enabled)
        self.row.update({
            "elapsed_seconds": round(time.monotonic() - self.tstate.started_at, 3),
            "best_fitness_generation": round(best_genome.fitness or 0.0, 3),
            "best_fitness_run": round(self.tstate.best_fitness, 3),
            "avg_fitness": round(mean(fitnesses), 3),
            "stdev_fitness": round(stdev(fitnesses), 3) if len(fitnesses) > 1 else 0.0,
            "best_genome_id": best_genome.key,
            "best_species_id": species_id,
            "best_nodes": len(best_genome.nodes),
            "best_connections": len(best_genome.connections),
            "best_enabled_connections": enabled_connections,
        })
        self.row.update(self.tstate.last_generation_metrics)

    def info(self, msg):
        match = re.search(r"Mean genetic distance ([0-9.]+), standard deviation ([0-9.]+)", msg)
        if match:
            self.row["mean_genetic_distance"] = float(match.group(1))
            self.row["genetic_distance_stdev"] = float(match.group(2))

    def end_generation(self, _config, population, species_set):
        self._ensure_open()
        species = species_set.species
        stagnations = [self.generation - s.last_improved for s in species.values()]
        self.row.update({
            "generation_time_seconds": round(time.monotonic() - self.generation_started_at, 3),
            "species_count": len(species),
            "species_sizes": ";".join(str(len(s.members)) for _, s in sorted(species.items())),
            "max_species_stagnation": max(stagnations, default=0),
        })
        self.writer.writerow({name: self.row.get(name, "") for name in self.FIELDNAMES})
        self.file.flush()

    def close(self):
        if self.file is not None:
            self.file.close()


class ExtinctionTracker(neat.reporting.BaseReporter):
    """Acumula IDs das espécies removidas por estagnação e loga a cada geração."""

    def __init__(self):
        self.extinct_ids: list[int] = []
        self._pending: list[int] = []

    def species_stagnant(self, sid, _species):
        self._pending.append(sid)

    def end_generation(self, _config, _population, _species_set):
        self.extinct_ids.extend(self._pending)
        ids_str = ", ".join(f"#{sid}" for sid in self.extinct_ids) if self.extinct_ids else "—"
        suffix = ""
        if self._pending:
            suffix = " (esta geração: " + ", ".join(f"#{sid}" for sid in self._pending) + ")"
        log.info("Population extinctions: %d [%s]%s", len(self.extinct_ids), ids_str, suffix)
        self._pending = []


class IntermissionReporter(neat.reporting.BaseReporter):
    """Mostra a pausa visual depois que os reporters já salvaram a geração."""

    def __init__(self, surface: pygame.Surface, brain: BrainViz, tstate: TrainerState):
        self.surface = surface
        self.brain = brain
        self.tstate = tstate

    def end_generation(self, _config, _population, _species_set):
        _intermission(self.surface, self.brain, self.tstate)


def _eval_genomes_factory(surface: pygame.Surface, hud: HUD, brain: BrainViz, neat_config, population):
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

        # 0 = sem limite (corre até todos morrerem). Caso contrário, converte segundos em frames.
        max_frames = config.MAX_GENERATION_SECONDS * config.FPS if config.MAX_GENERATION_SECONDS > 0 else 0
        top_speed_frame_limit = (
            config.MAX_SECONDS_AT_TOP_SPEED * config.FPS if config.MAX_SECONDS_AT_TOP_SPEED > 0 else 0
        )
        top_speed_frames = 0
        stopped_by_top_speed = False
        frame = 0
        while any(d.alive for d in state.dinos) and (max_frames == 0 or frame < max_frames):
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
                try:
                    TSTATE.current_species_id = population.species.get_species_id(ge[best_idx].key)
                except (KeyError, AttributeError):
                    TSTATE.current_species_id = None
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
                elapsed_seconds=time.monotonic() - TSTATE.started_at,
            )
            pygame.display.flip()
            brain.draw(TSTATE, dino_count=sum(1 for d in state.dinos if d.alive))
            clock.tick(config.FPS)

            if top_speed_frame_limit > 0 and state.world.speed >= config.GAME_SPEED_MAX:
                top_speed_frames += 1
                if top_speed_frames >= top_speed_frame_limit:
                    stopped_by_top_speed = True
                    log.info(
                        "geração %d encerrada por guardrail: %ds em GAME_SPEED_MAX (%s)",
                        TSTATE.generation, config.MAX_SECONDS_AT_TOP_SPEED, config.GAME_SPEED_MAX,
                    )
                    break
            else:
                top_speed_frames = 0

        for i, g in enumerate(ge):
            d = state.dinos[i]
            g.fitness = d.fitness + d.obstacles_passed * config.POINTS_PER_OBSTACLE
            if g.fitness > TSTATE.best_fitness:
                TSTATE.best_fitness = g.fitness

        best = max(ge, key=lambda g: g.fitness)
        best_idx = ge.index(best)
        best_dino = state.dinos[best_idx]
        TSTATE.last_generation_metrics = {
            "best_obstacles_passed": best_dino.obstacles_passed,
            "best_km": round(state.world.km, 4),
            "best_speed_reached": round(state.world.speed, 3),
            "stopped_by_top_speed": stopped_by_top_speed,
        }
        checkpoint.save_best(best)
        log.info(
            "geração %d encerrada | melhor=%.1f | recorde=%.1f | nós=%d | conex=%d",
            TSTATE.generation, best.fitness, TSTATE.best_fitness,
            len(best.nodes),
            sum(1 for c in best.connections.values() if c.enabled),
        )

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


_INT_NEAT_ATTRS = {"max_stagnation", "species_elitism", "elitism"}


def _apply_neat_overrides(neat_config) -> None:
    for path, value in config.NEAT_OVERRIDES.items():
        if value is None:
            continue
        section_name, attr = path.split(".")
        section = getattr(neat_config, section_name)
        coerced = int(value) if attr in _INT_NEAT_ATTRS else float(value)
        setattr(section, attr, coerced)
        log.info("NEAT override aplicado: %s.%s=%s", section_name, attr, coerced)


def run(resume: bool = False, generations: int | None = None):
    if generations is None:
        generations = config.MAX_GENERATIONS if config.MAX_GENERATIONS > 0 else None
    log.info("modo IA NEAT | resume=%s | max_geracoes=%s | pop_size=%d",
             resume, generations if generations is not None else "ilimitado",
             config.POPULATION_SIZE)
    TSTATE.started_at = time.monotonic()
    live_server = None
    try:
        from src.reports import live
        live_server = live.start_background()
        log.info("dashboard live iniciado em %s (refresh automático: %ds)",
                 live_server.url, live.REFRESH_SECONDS)
    except Exception:
        log.exception("não foi possível iniciar o dashboard live")

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
    neat_config.pop_size = config.POPULATION_SIZE
    log.info("NEAT pop_size efetivo=%d", neat_config.pop_size)
    _apply_neat_overrides(neat_config)

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

    experiment_reporter = ExperimentReporter(TSTATE, neat_config, resume)
    TSTATE.run_id = experiment_reporter.run_id
    pop.add_reporter(neat.StdOutReporter(True))
    pop.add_reporter(neat.StatisticsReporter())
    pop.add_reporter(experiment_reporter)
    pop.add_reporter(ExtinctionTracker())
    pop.add_reporter(IntermissionReporter(surface, brain, TSTATE))

    eval_fn = _eval_genomes_factory(surface, hud, brain, neat_config, pop)
    try:
        pop.run(eval_fn, generations)
    except SystemExit:
        log.info("treino interrompido pelo usuário")
        pygame.quit()
        raise
    finally:
        experiment_reporter.close()
        if live_server is not None:
            live_server.close()
            log.info("dashboard live encerrado")
        pygame.quit()
        log.info("modo IA encerrado | última geração=%d | recorde=%.1f | relatório=%s",
                 TSTATE.generation, TSTATE.best_fitness, experiment_reporter.path)
