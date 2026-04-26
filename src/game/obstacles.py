import colorsys
import random
import pygame
from src import config
from src.game import assets

CACTUS_COLOR = (40, 120, 40)
BIRD_COLOR = (180, 100, 40)

BIRD_ANIM_TICK = 8  # frames de jogo entre uma batida de asa e outra


def _random_vivid_color() -> tuple[int, int, int]:
    """Cor saturada aleatória — usada nos pássaros pra diferenciar cada um."""
    h = random.random()
    s = random.uniform(0.55, 0.85)
    v = random.uniform(0.75, 0.95)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class Obstacle:
    kind: str = "obstacle"
    sprite_name: str = ""

    def __init__(self, x: int, y: int, w: int, h: int, color: tuple):
        self.x = float(x)
        self.y = y
        self.width = w
        self.height = h
        self.color = color
        self.passed = False

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), self.y, self.width, self.height)

    def update(self, speed: float):
        self.x -= speed

    def draw(self, surface: pygame.Surface):
        sprite = assets.get(self.sprite_name, (self.width, self.height)) if self.sprite_name else None
        if sprite is not None:
            surface.blit(sprite, (int(self.x), self.y))
        else:
            pygame.draw.rect(surface, self.color, self.rect)


class Cactus(Obstacle):
    kind = "cactus"

    def __init__(self, x: int):
        variant, w, h = random.choice([("small", 18, 35), ("med", 25, 45), ("big", 30, 55)])
        y = config.GROUND_Y - h
        super().__init__(x, y, w, h, CACTUS_COLOR)
        self.sprite_name = f"cactus_{variant}"

    def draw(self, surface: pygame.Surface):
        sprite = assets.get(self.sprite_name, (self.width, self.height))
        if sprite is not None:
            surface.blit(sprite, (int(self.x), self.y))
            return
        x, y, w, h = int(self.x), self.y, self.width, self.height
        body_w = max(6, w // 3)
        body_x = x + (w - body_w) // 2
        dark = (30, 90, 30)
        pygame.draw.rect(surface, CACTUS_COLOR, (body_x, y, body_w, h), border_radius=2)
        pygame.draw.rect(surface, dark, (body_x, y, body_w, h), 1, border_radius=2)
        arm_h = h // 3
        arm_w = max(4, body_w // 2)
        arm_y = y + h // 3
        pygame.draw.rect(surface, CACTUS_COLOR, (x, arm_y + arm_h - arm_w, arm_w, arm_w))
        pygame.draw.rect(surface, CACTUS_COLOR, (x, arm_y, arm_w, arm_h))
        pygame.draw.rect(surface, dark, (x, arm_y, arm_w, arm_h), 1)
        pygame.draw.rect(surface, CACTUS_COLOR, (x + w - arm_w, arm_y + arm_h - arm_w, arm_w, arm_w))
        pygame.draw.rect(surface, CACTUS_COLOR, (x + w - arm_w, arm_y, arm_w, arm_h))
        pygame.draw.rect(surface, dark, (x + w - arm_w, arm_y, arm_w, arm_h), 1)
        for i in range(2, h - 2, 6):
            pygame.draw.line(surface, dark, (body_x + body_w // 2, y + i), (body_x + body_w // 2, y + i + 2), 1)


class Bird(Obstacle):
    kind = "bird"

    def __init__(self, x: int):
        altitude = random.choice(["high", "mid"])
        h = 25
        w = 40
        if altitude == "high":
            y = config.GROUND_Y - 75
        else:
            y = config.GROUND_Y - 45
        super().__init__(x, y, w, h, BIRD_COLOR)
        self.sprite_name = "bird"  # mantém pro fallback do PNG estático
        self.tint = _random_vivid_color()
        self._anim_frame = 0
        self._anim_tick = 0

    def _frames(self) -> list[pygame.Surface]:
        # sprite maior que o hitbox; colisão segue 40x25
        visual = (self.width + 24, self.height + 14)
        return assets.get_animation_tinted("bird", "bird", visual, self.tint)

    def update(self, speed: float):
        super().update(speed)
        self._anim_tick += 1
        if self._anim_tick >= BIRD_ANIM_TICK:
            self._anim_tick = 0
            frames = self._frames()
            if frames:
                self._anim_frame = (self._anim_frame + 1) % len(frames)

    def draw(self, surface: pygame.Surface):
        frames = self._frames()
        if frames:
            sprite = frames[self._anim_frame % len(frames)]
            bx = int(self.x) - (sprite.get_width() - self.width) // 2
            by = self.y - (sprite.get_height() - self.height) // 2
            surface.blit(sprite, (bx, by))
        else:
            super().draw(surface)


class Spawner:
    def __init__(self):
        self.next_spawn = 60
        self.frame = 0

    def update(self, obstacles: list, speed: float, allow_birds: bool):
        self.frame += 1
        if self.frame >= self.next_spawn:
            self.frame = 0
            x = config.WINDOW_WIDTH + 20
            if allow_birds and random.random() < 0.25:
                obstacles.append(Bird(x))
            else:
                obstacles.append(Cactus(x))
            base_gap = max(config.OBSTACLE_MIN_GAP_FRAMES, int(180 - speed * 4))
            self.next_spawn = random.randint(base_gap, base_gap + 90)

    def reset(self):
        self.frame = 0
        self.next_spawn = 60
