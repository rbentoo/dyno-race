import random
import pygame
from src import config

GROUND_FILL = (170, 130, 80)      # marrom areia
GROUND_LINE = (90, 60, 30)        # marrom escuro pra borda
GROUND_DETAIL = (130, 95, 55)     # tracinhos/pedras
SKY_TOP = (120, 180, 230)
SKY_BOTTOM = (200, 230, 245)
CLOUD_COLOR = (255, 255, 255)
CLOUD_SHADOW = (220, 230, 240)
CLOUD_COUNT = 10


class World:
    """Estado compartilhado: chão, nuvens, velocidade."""

    def __init__(self):
        self.speed = float(config.GAME_SPEED_INITIAL)
        self.distance = 0.0
        self.frames = 0
        # nuvem: (x, y, escala) — escala dá variedade de tamanho
        self.clouds: list[tuple[float, int, float]] = [
            (
                random.randint(0, config.WINDOW_WIDTH),
                random.randint(15, 130),
                random.uniform(0.7, 1.6),
            )
            for _ in range(CLOUD_COUNT)
        ]
        self.ground_offset = 0.0
        self._sky = self._build_sky()

    def _build_sky(self) -> pygame.Surface:
        """Pré-renderiza um gradiente vertical do céu uma única vez."""
        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        h = config.WINDOW_HEIGHT
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (config.WINDOW_WIDTH, y))
        return surf

    def reset(self):
        self.speed = float(config.GAME_SPEED_INITIAL)
        self.distance = 0.0
        self.frames = 0
        self.ground_offset = 0.0

    def update(self):
        self.frames += 1
        self.distance += self.speed
        # acelera ~ a cada 500 frames
        if self.speed < config.GAME_SPEED_MAX and self.frames % 500 == 0:
            self.speed += 0.5
        # nuvens (parallax: nuvem maior anda mais rápido)
        new_clouds = []
        for x, y, scale in self.clouds:
            x -= self.speed * (0.15 + scale * 0.15)
            if x < -120 * scale:
                x = config.WINDOW_WIDTH + random.randint(20, 250)
                y = random.randint(15, 130)
                scale = random.uniform(0.7, 1.6)
            new_clouds.append((x, y, scale))
        self.clouds = new_clouds
        self.ground_offset = (self.ground_offset + self.speed) % 40

    def _draw_cloud(self, surface, x, y, scale):
        """Nuvem fofa: 3 elipses sobrepostas + sombra leve embaixo."""
        w = int(60 * scale)
        h = int(22 * scale)
        pygame.draw.ellipse(surface, CLOUD_SHADOW, (int(x) + 4, int(y) + h // 3, w, h))
        pygame.draw.ellipse(surface, CLOUD_COLOR, (int(x), int(y), w, h))
        pygame.draw.ellipse(surface, CLOUD_COLOR,
                            (int(x) + w // 4, int(y) - h // 3, w // 2, h))
        pygame.draw.ellipse(surface, CLOUD_COLOR,
                            (int(x) + w // 2, int(y) + h // 6, w // 2, int(h * 0.85)))

    def draw(self, surface: pygame.Surface):
        surface.blit(self._sky, (0, 0))
        for x, y, scale in self.clouds:
            self._draw_cloud(surface, x, y, scale)
        pygame.draw.rect(
            surface, GROUND_FILL,
            (0, config.GROUND_Y, config.WINDOW_WIDTH, config.WINDOW_HEIGHT - config.GROUND_Y),
        )
        pygame.draw.line(
            surface, GROUND_LINE,
            (0, config.GROUND_Y),
            (config.WINDOW_WIDTH, config.GROUND_Y), 2,
        )
        for i in range(-1, config.WINDOW_WIDTH // 40 + 2):
            x = i * 40 - int(self.ground_offset)
            pygame.draw.line(surface, GROUND_DETAIL, (x, config.GROUND_Y + 8), (x + 14, config.GROUND_Y + 8), 2)
            pygame.draw.line(surface, GROUND_DETAIL, (x + 20, config.GROUND_Y + 18), (x + 28, config.GROUND_Y + 18), 2)

    @property
    def km(self) -> float:
        return self.distance / 10_000

    @property
    def seconds(self) -> float:
        return self.frames / config.FPS
