"""Segunda janela: desenha a rede neural do melhor dino vivo, ao vivo."""
import math
import pygame
from src import config, logger
from src.ai import sensors
from src.game.dino import color_name, COLOR_ALIVE
from src.viz.stats import StatsSampler

log = logger.get(__name__)


# Paleta
BG_TOP = (18, 22, 32)
BG_BOTTOM = (28, 32, 46)
TEXT = (235, 235, 245)
DIM = (140, 145, 165)
SUBTLE = (80, 85, 100)
HEADER_BG = (12, 14, 22, 220)
PANEL_BG = (12, 14, 22, 180)
PANEL_BORDER = (60, 70, 100, 160)

INPUT_COL = (88, 158, 230)      # azul claro
OUTPUT_COL = (240, 165, 90)     # laranja
OUTPUT_ACTIVE = (110, 230, 140)  # verde quando dispara
HIDDEN_COL = (180, 130, 230)    # roxo

EDGE_POS = (90, 180, 255)
EDGE_NEG = (240, 95, 95)

CPU_COLOR = (110, 230, 140)
RAM_COLOR = (240, 165, 90)
GRID = (60, 70, 90)

STATS_PANEL_H = 110
LEGEND_PANEL_H = 86

# atualiza a cada N frames de jogo (jogo roda a 60fps, brain a ~20fps)
DRAW_EVERY = 3

NODE_RADIUS = 16


class BrainViz:
    def __init__(self):
        try:
            from pygame._sdl2 import Window, Renderer
            self.window = Window(
                "Dyno Race — Cérebro",
                size=(config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT),
            )
            self.window.position = (50, 400)
            self.renderer = Renderer(self.window)
            self.surface = pygame.Surface((config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT))
            self._mode = "sdl2"
        except Exception as exc:
            log.warning("pygame._sdl2.Window indisponível (%s) — usando fallback sem segunda janela", exc)
            self.surface = pygame.Surface((config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT))
            self._mode = "fallback"
            self.window = None

        self.font_xs = pygame.font.SysFont("monospace", 11)
        self.font = pygame.font.SysFont("monospace", 13)
        self.font_b = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_title = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_action = pygame.font.SysFont("monospace", 22, bold=True)

        self._bg = self._build_bg()
        self._frame = 0
        self.stats = StatsSampler()
        self._dino_count = 0

    # ---------- Background gradiente ----------
    def _build_bg(self) -> pygame.Surface:
        surf = pygame.Surface((config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT))
        h = config.BRAIN_WINDOW_HEIGHT
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
            g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
            b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (config.BRAIN_WINDOW_WIDTH, y))
        return surf

    # ---------- Layout ----------
    def _layout(self, hidden_keys, n_in, n_out):
        w = config.BRAIN_WINDOW_WIDTH
        # área útil: do header (y=70) ao painel de stats (acima da legenda)
        top = 90
        bottom = config.BRAIN_WINDOW_HEIGHT - 110 - STATS_PANEL_H
        h = bottom - top

        col_in_x = 110
        col_out_x = w - 110
        col_hid_x = w // 2

        positions = {}
        for i in range(n_in):
            y = top + h * (i + 1) / (n_in + 1)
            positions[-i - 1] = (col_in_x, y)
        for i in range(n_out):
            y = top + h * (i + 1) / (n_out + 1)
            positions[i] = (col_out_x, y)
        for i, k in enumerate(hidden_keys):
            y = top + h * (i + 1) / (len(hidden_keys) + 1)
            # leve dispersão horizontal pra hidden não ficar tudo empilhado
            x = col_hid_x + (i % 2) * 30 - 15
            positions[k] = (x, y)
        return positions, (col_in_x, col_out_x, col_hid_x), top, bottom

    # ---------- Header ----------
    def _draw_header(self, s, tstate, n_nodes, n_edges):
        bar = pygame.Surface((config.BRAIN_WINDOW_WIDTH, 60), pygame.SRCALPHA)
        bar.fill(HEADER_BG)
        s.blit(bar, (0, 0))
        title = self.font_title.render("REDE NEURAL — DYNO BRAIN", True, TEXT)
        s.blit(title, (16, 10))

        action = tstate.last_action or "—"
        color = OUTPUT_ACTIVE if action in ("PULAR", "ABAIXAR") else DIM
        act_label = self.font_xs.render("AÇÃO ATUAL", True, DIM)
        act_value = self.font_action.render(action, True, color)
        act_x = config.BRAIN_WINDOW_WIDTH - act_value.get_width() - 16
        s.blit(act_label, (act_x, 6))
        s.blit(act_value, (act_x, 22))

        run_id = getattr(tstate, "run_id", "") or "—"
        run_label = self.font_xs.render("RUN ID", True, DIM)
        run_value = self.font_action.render(run_id, True, TEXT)
        run_x = act_x - run_value.get_width() - 32
        s.blit(run_label, (run_x, 6))
        s.blit(run_value, (run_x, 22))

        meta = self.font.render(
            f"geração {tstate.generation}    nós {n_nodes}    conexões {n_edges}",
            True, DIM,
        )
        s.blit(meta, (16, 36))

        dino = getattr(tstate, "current_dino", None)
        if dino is not None and getattr(dino, "base_color", COLOR_ALIVE) != COLOR_ALIVE:
            dino_color = dino.base_color
            label = self.font_xs.render("DINO ATUAL", True, DIM)
            name = self.font_action.render(color_name(dino_color), True, dino_color)
            x = 16 + max(title.get_width(), 280) + 24
            s.blit(label, (x, 6))
            sw_x = x + name.get_width() + 18
            pygame.draw.circle(s, dino_color, (sw_x, 36), 11)
            pygame.draw.circle(s, TEXT, (sw_x, 36), 11, 1)
            s.blit(name, (x, 22))

    # ---------- Column labels ----------
    def _draw_column_labels(self, s, cols, top):
        col_in, col_out, col_hid = cols
        for x, label in [(col_in, "ENTRADAS"), (col_hid, "OCULTOS"), (col_out, "SAÍDAS")]:
            txt = self.font_b.render(label, True, DIM)
            s.blit(txt, (x - txt.get_width() // 2, top - 28))

    # ---------- Edges ----------
    def _draw_edges(self, s, genome, positions, inputs):
        """Desenha conexões. Linha pontilhada se sinal é fraco; sólida + glow se forte."""
        for cg in genome.connections.values():
            if not cg.enabled:
                continue
            in_node, out_node = cg.key
            if in_node not in positions or out_node not in positions:
                continue
            p1 = positions[in_node]
            p2 = positions[out_node]

            color = EDGE_POS if cg.weight >= 0 else EDGE_NEG
            thick = max(1, int(min(abs(cg.weight) * 1.6, 5)))

            # intensidade do sinal: |entrada * peso|
            signal = 0.0
            if in_node < 0 and -in_node - 1 < len(inputs):
                signal = abs(inputs[-in_node - 1] * cg.weight)
            signal_norm = min(1.0, signal / 2.0)

            if signal_norm > 0.15:
                alpha = int(40 + signal_norm * 140)
                glow_color = (*color, alpha)
                glow_thick = thick + 4
                glow = pygame.Surface((config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(glow, glow_color, p1, p2, glow_thick)
                s.blit(glow, (0, 0))
                pygame.draw.line(s, color, p1, p2, thick)
            else:
                self._dashed_line(s, color, p1, p2, thick, dash=8, gap=6)

    def _dashed_line(self, surf, color, p1, p2, width, dash=8, gap=6):
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        ux, uy = dx / dist, dy / dist
        steps = int(dist // (dash + gap))
        for i in range(steps + 1):
            sx = x1 + ux * i * (dash + gap)
            sy = y1 + uy * i * (dash + gap)
            ex = sx + ux * dash
            ey = sy + uy * dash
            pygame.draw.line(surf, color, (sx, sy), (ex, ey), width)

    # ---------- Nodes ----------
    def _draw_node(self, s, pos, color, activation, label, side, value=None):
        x, y = int(pos[0]), int(pos[1])
        intensity = max(0.0, min(1.0, abs(activation)))
        glow_r = int(NODE_RADIUS + 4 + intensity * 18)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for i in range(3, 0, -1):
            r = int(NODE_RADIUS + i * 5 + intensity * 12)
            a = int(intensity * (180 // i))
            pygame.draw.circle(glow, (*color, a), (glow_r, glow_r), r)
        s.blit(glow, (x - glow_r, y - glow_r))
        pygame.draw.circle(s, color, (x, y), NODE_RADIUS)
        pygame.draw.circle(s, TEXT, (x, y), NODE_RADIUS, 1)

        txt = self.font.render(label, True, TEXT)
        if side == "left":
            s.blit(txt, (x - NODE_RADIUS - 8 - txt.get_width(), y - 8))
            if value is not None:
                v = self.font_xs.render(f"{value:+.2f}", True, DIM)
                s.blit(v, (x - NODE_RADIUS - 8 - v.get_width(), y + 6))
        elif side == "right":
            s.blit(txt, (x + NODE_RADIUS + 8, y - 8))
            if value is not None:
                v = self.font_xs.render(f"{value:+.2f}", True, DIM)
                s.blit(v, (x + NODE_RADIUS + 8, y + 6))
        else:
            s.blit(txt, (x - txt.get_width() // 2, y + NODE_RADIUS + 4))

    # ---------- Stats CPU/RAM ----------
    def _draw_sparkline(self, s, x, y, w, h, history, color, max_val, unit="%"):
        frame = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(frame, (255, 255, 255, 18), frame.get_rect(), border_radius=3)
        pygame.draw.rect(frame, PANEL_BORDER, frame.get_rect(), width=1, border_radius=3)
        s.blit(frame, (x, y))

        mid_y = y + h // 2
        pygame.draw.line(s, GRID, (x + 2, mid_y), (x + w - 2, mid_y), 1)

        max_label = self.font_xs.render(f"{int(max_val)}{unit}", True, DIM)
        zero_label = self.font_xs.render(f"0{unit}", True, DIM)
        s.blit(max_label, (x + w - max_label.get_width() - 4, y + 2))
        s.blit(zero_label, (x + w - zero_label.get_width() - 4, y + h - zero_label.get_height() - 2))

        if len(history) < 2:
            return
        n = len(history)
        pts = []
        for i, v in enumerate(history):
            px = x + int(w * i / max(1, n - 1))
            py = y + h - int(h * min(v, max_val) / max_val)
            pts.append((px, max(y, py)))
        poly = [(pts[0][0], y + h)] + pts + [(pts[-1][0], y + h)]
        shade = pygame.Surface((config.BRAIN_WINDOW_WIDTH, config.BRAIN_WINDOW_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(shade, (*color, 80), poly)
        s.blit(shade, (0, 0))
        pygame.draw.lines(s, color, False, pts, 2)

    def _draw_stats(self, s):
        self.stats.sample()
        y = config.BRAIN_WINDOW_HEIGHT - 16 - LEGEND_PANEL_H - STATS_PANEL_H - 8
        w = config.BRAIN_WINDOW_WIDTH - 32
        panel = pygame.Surface((w, STATS_PANEL_H), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_BG, panel.get_rect(), border_radius=6)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), width=1, border_radius=6)
        s.blit(panel, (16, y))

        s.blit(self.font_b.render("CPU / RAM DO PROCESSO", True, TEXT), (28, y + 8))
        meta = self.font_xs.render(
            f"dinos vivos {self._dino_count}    cores {self.stats.cpu_count}    "
            f"amostra {self.stats.interval:.1f}s",
            True, DIM,
        )
        s.blit(meta, (28, y + 28))

        cpu_txt = self.font_b.render(f"CPU  {self.stats.last_cpu:5.1f}%", True, CPU_COLOR)
        ram_txt = self.font_b.render(
            f"RAM  {self.stats.last_ram_mb:6.1f} MB ({self.stats.last_ram_pct:.2f}%)",
            True, RAM_COLOR,
        )
        s.blit(cpu_txt, (28, y + 50))
        s.blit(ram_txt, (28, y + 70))

        spark_w = 280
        spark_h = 38
        spark_x = config.BRAIN_WINDOW_WIDTH - 16 - spark_w - 12
        # escala da RAM: arredonda pro próximo múltiplo de 5% acima do uso atual
        ram_max = max(5.0, math.ceil((self.stats.last_ram_pct or 1) * 1.5 / 5.0) * 5.0)
        self._draw_sparkline(s, spark_x, y + 30, spark_w, spark_h,
                             self.stats.cpu_hist, CPU_COLOR, max_val=100.0, unit="%")
        self._draw_sparkline(s, spark_x, y + 30 + spark_h + 6, spark_w, spark_h - 4,
                             self.stats.ram_hist, RAM_COLOR, max_val=ram_max, unit="%")

    # ---------- Footer (legenda) ----------
    def _draw_legend(self, s):
        panel_w = config.BRAIN_WINDOW_WIDTH - 32
        y = config.BRAIN_WINDOW_HEIGHT - 16 - LEGEND_PANEL_H
        panel = pygame.Surface((panel_w, LEGEND_PANEL_H), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_BG, panel.get_rect(), border_radius=6)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), width=1, border_radius=6)
        s.blit(panel, (16, y))

        def slot(items, count, idx):
            return 16 + int(panel_w * (idx + 0.5) / count) - items // 2

        y0 = y + 16
        edges = [
            ("line", EDGE_POS, "peso positivo (excita)"),
            ("line", EDGE_NEG, "peso negativo (inibe)"),
            ("dash", SUBTLE, "conexão dormente"),
        ]
        for i, (kind, color, label) in enumerate(edges):
            txt = self.font_xs.render(label, True, TEXT)
            block_w = 30 + 10 + txt.get_width()
            x0 = slot(block_w, len(edges), i)
            if kind == "line":
                pygame.draw.line(s, color, (x0, y0 + 5), (x0 + 30, y0 + 5), 3)
            else:
                self._dashed_line(s, color, (x0, y0 + 5), (x0 + 30, y0 + 5), 2)
            s.blit(txt, (x0 + 40, y0))

        y1 = y + 50
        nodes = [
            (INPUT_COL, "entrada"),
            (HIDDEN_COL, "oculto (criado pela evolução)"),
            (OUTPUT_COL, "saída"),
            (OUTPUT_ACTIVE, "saída disparada"),
        ]
        for i, (color, label) in enumerate(nodes):
            txt = self.font_xs.render(label, True, TEXT)
            block_w = 14 + 8 + txt.get_width()
            x0 = slot(block_w, len(nodes), i)
            pygame.draw.circle(s, color, (x0 + 7, y1 + 7), 6)
            s.blit(txt, (x0 + 22, y1))

    # ---------- Main draw ----------
    def draw(self, tstate, dino_count: int = 0):
        self._frame += 1
        if self._frame % DRAW_EVERY != 0:
            return
        self._dino_count = dino_count

        s = self.surface
        s.blit(self._bg, (0, 0))

        if tstate.current_genome is None:
            self._draw_header(s, tstate, 0, 0)
            empty = self.font.render("aguardando primeiro genoma…", True, DIM)
            s.blit(empty, empty.get_rect(center=(config.BRAIN_WINDOW_WIDTH // 2, config.BRAIN_WINDOW_HEIGHT // 2)))
            self._draw_stats(s)
            self._draw_legend(s)
            self._present()
            return

        genome = tstate.current_genome
        n_in = len(sensors.INPUT_LABELS)
        n_out = len(sensors.OUTPUT_LABELS)
        output_keys = list(range(n_out))
        hidden_keys = [k for k in genome.nodes.keys() if k not in output_keys]

        positions, cols, top, _ = self._layout(hidden_keys, n_in, n_out)

        n_edges = sum(1 for c in genome.connections.values() if c.enabled)
        self._draw_header(s, tstate, len(genome.nodes), n_edges)
        self._draw_column_labels(s, cols, top)

        self._draw_edges(s, genome, positions, tstate.last_inputs)

        for i in range(n_in):
            val = tstate.last_inputs[i] if i < len(tstate.last_inputs) else 0.0
            self._draw_node(s, positions[-i - 1], INPUT_COL, val,
                            sensors.INPUT_LABELS[i], side="left", value=val)
        for k in hidden_keys:
            self._draw_node(s, positions[k], HIDDEN_COL, 0.7, f"h{k}", side="top")
        for i in range(n_out):
            val = tstate.last_outputs[i] if i < len(tstate.last_outputs) else 0.0
            active = val > 0.5
            color = OUTPUT_ACTIVE if active else OUTPUT_COL
            self._draw_node(s, positions[i], color, val,
                            sensors.OUTPUT_LABELS[i], side="right", value=val)

        self._draw_stats(s)
        self._draw_legend(s)
        self._present()

    def _present(self):
        if self._mode == "sdl2":
            from pygame._sdl2 import Texture
            tex = Texture.from_surface(self.renderer, self.surface)
            self.renderer.clear()
            tex.draw()
            self.renderer.present()
