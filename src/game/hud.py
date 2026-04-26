import pygame
from src import config
from src.game import assets

TEXT_COLOR = (30, 30, 40)
PANEL_BG = (255, 255, 255, 180)     # ~70% opacidade
PANEL_BORDER = (60, 80, 120, 220)
TROPHY_COLOR = (220, 170, 30)
TROPHY_DARK = (140, 100, 20)

PANEL_X = 8
PANEL_Y = 6
PANEL_PAD_X = 10
PANEL_PAD_Y = 6
TROPHY_ICON_SIZE = 18


def _procedural_trophy(size: int) -> pygame.Surface:
    """Mini troféu desenhado em runtime — usado se assets/trophy.png não existir."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cup = pygame.Rect(size * 0.25, size * 0.15, size * 0.5, size * 0.45)
    pygame.draw.ellipse(s, TROPHY_COLOR, cup)
    pygame.draw.ellipse(s, TROPHY_DARK, cup, 1)
    pygame.draw.arc(s, TROPHY_DARK, (size * 0.10, size * 0.20, size * 0.30, size * 0.30),
                    0.5, 2.7, 2)
    pygame.draw.arc(s, TROPHY_DARK, (size * 0.60, size * 0.20, size * 0.30, size * 0.30),
                    0.5, 2.7, 2)
    pygame.draw.rect(s, TROPHY_COLOR, (size * 0.42, size * 0.55, size * 0.16, size * 0.20))
    pygame.draw.rect(s, TROPHY_COLOR, (size * 0.30, size * 0.78, size * 0.40, size * 0.12),
                     border_radius=2)
    pygame.draw.rect(s, TROPHY_DARK, (size * 0.30, size * 0.78, size * 0.40, size * 0.12),
                     1, border_radius=2)
    return s


class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("monospace", 14, bold=True)
        self.big = pygame.font.SysFont("monospace", 22, bold=True)
        self.thresholds = config.trophy_thresholds()
        self.trophy_icon = (
            assets.get("trophy", (TROPHY_ICON_SIZE, TROPHY_ICON_SIZE))
            or _procedural_trophy(TROPHY_ICON_SIZE)
        )

    def trophies_earned(self, score: int) -> int:
        return sum(1 for t in self.thresholds if score >= t)

    def _draw_panel(self, surface: pygame.Surface, lines: list[str], trophy_line: int = -1):
        """Renderiza linhas (string vazia = espaçador) dentro de painel translúcido.
        Se trophy_line >= 0, desenha o ícone do troféu no fim daquela linha.
        """
        line_h = self.font.get_height()
        rendered = [self.font.render(ln, True, TEXT_COLOR) if ln else None for ln in lines]
        max_text_w = max((r.get_width() for r in rendered if r is not None), default=0)
        icon_extra = (TROPHY_ICON_SIZE + 6) if trophy_line >= 0 else 0
        w = max_text_w + PANEL_PAD_X * 2 + icon_extra
        h = sum(line_h if r is None else r.get_height() for r in rendered) \
            + PANEL_PAD_Y * 2 + (len(rendered) - 1) * 2
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_BG, panel.get_rect(), border_radius=6)
        pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), width=1, border_radius=6)
        surface.blit(panel, (PANEL_X, PANEL_Y))
        y = PANEL_Y + PANEL_PAD_Y
        for i, r in enumerate(rendered):
            if r is None:
                y += line_h // 2 + 2
                continue
            surface.blit(r, (PANEL_X + PANEL_PAD_X, y))
            if i == trophy_line:
                icon_x = PANEL_X + PANEL_PAD_X + max_text_w + 4
                icon_y = y + (r.get_height() - TROPHY_ICON_SIZE) // 2
                surface.blit(self.trophy_icon, (icon_x, icon_y))
            y += r.get_height() + 2

    def draw_human(self, surface: pygame.Surface, *, score: int, km: float, seconds: float,
                   speed: float, speed_max: float, dead: bool):
        trophies = self.trophies_earned(score)
        next_t = next((t for t in self.thresholds if score < t), None)
        trophy_str = f"{trophies}x" if trophies > 0 else "—"
        speed_str = f"{speed:.1f}/{speed_max:.0f}"
        lines = [
            f"PONTOS     {score:>9}",
            f"CHECKPOINT {next_t if next_t else '—':>9}",
            f"TROFEU     {trophy_str:>9}",
            "",
            f"DISTANCIA  {km:>6.2f} KM",
            f"TEMPO      {seconds:>7.1f}s",
            f"VELOCIDADE {speed_str:>9}",
        ]
        self._draw_panel(surface, lines, trophy_line=2)
        if dead:
            msg = self.big.render("GAME OVER — ESPAÇO p/ reiniciar", True, (180, 40, 40))
            r = msg.get_rect(center=(config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2 - 20))
            pad = 12
            box = pygame.Surface((r.width + pad * 2, r.height + pad), pygame.SRCALPHA)
            pygame.draw.rect(box, PANEL_BG, box.get_rect(), border_radius=8)
            pygame.draw.rect(box, PANEL_BORDER, box.get_rect(), width=1, border_radius=8)
            surface.blit(box, (r.x - pad, r.y - pad // 2))
            surface.blit(msg, r)

    def draw_ai(self, surface: pygame.Surface, *, generation: int, alive: int, total: int,
                best_fitness: float, gen_best: float, km: float,
                speed: float, speed_max: float):
        lines = [
            f"GERACAO    {generation}",
            f"VIVOS      {alive:>2}/{total}",
            f"FIT GER    {gen_best:>7.1f}",
            f"FIT MAX    {best_fitness:>7.1f}",
            "",
            f"DISTANCIA  {km:>6.2f} KM",
            f"VELOCIDADE {speed:>4.1f}/{speed_max:.0f}",
        ]
        self._draw_panel(surface, lines)
