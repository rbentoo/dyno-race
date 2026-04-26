import colorsys
import pygame
from src import config
from src.game import assets

GRAVITY = 0.9
JUMP_VELOCITY = -14
DUCK_HEIGHT = 26
RUN_HEIGHT = 44
WIDTH = 40

# tamanho VISUAL do sprite (maior que o hitbox pra ficar bonito).
# o hitbox de colisão segue WIDTH x RUN_HEIGHT — sprite só decora.
SPRITE_W = 80
SPRITE_H = 80
DUCK_SPRITE_H = 60

COLOR_ALIVE = (60, 60, 60)
GHOST_ALPHA = 18  # mortos bem fantasmagóricos, pra não tampar os vivos

# velocidade da animação: avança 1 frame a cada N frames de jogo (60fps)
ANIM_TICK = {
    "run": 4,    # ~15fps — pernas correndo
    "jump": 5,   # animação de pulo lenta o suficiente pra ler
    "dead": 6,   # morte arrastada
    "idle": 6,
}


def color_for_index(i: int, _total: int = 0) -> tuple[int, int, int]:
    h = (i * 0.6180339887) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.88)
    return (int(r * 255), int(g * 255), int(b * 255))


# regiões de matiz (em fração 0..1) → nome amigável
_HUE_NAMES = [
    (0.04, "VERMELHO"),
    (0.10, "LARANJA"),
    (0.18, "AMARELO"),
    (0.30, "VERDE-LIMÃO"),
    (0.42, "VERDE"),
    (0.52, "CIANO"),
    (0.62, "AZUL"),
    (0.74, "VIOLETA"),
    (0.84, "ROXO"),
    (0.94, "ROSA"),
    (1.01, "VERMELHO"),
]


def color_name(rgb: tuple[int, int, int]) -> str:
    """RGB → nome amigável em PT-BR baseado no matiz HSV."""
    r, g, b = (c / 255 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.15:
        return "PRETO"
    if s < 0.12:
        return "CINZA" if v < 0.85 else "BRANCO"
    for limit, name in _HUE_NAMES:
        if h < limit:
            return name
    return "?"


# nomes de pasta/prefixo usados em assets/dino/{Prefix} (N).png
_ANIM_SOURCES = {
    "run": ("dino", "Run"),
    "jump": ("dino", "Jump"),
    "dead": ("dino", "Dead"),
    "idle": ("dino", "Idle"),
    "duck": ("dino", "Walk"),  # sem sprite de duck — Walk fica decente abaixado
}


class Dino:
    def __init__(self, x: int = 60, color: tuple | None = None):
        self.x = x
        self.width = WIDTH
        self.height = RUN_HEIGHT
        self.y = config.GROUND_Y - self.height
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.alive = True
        self.base_color = color or COLOR_ALIVE
        self.color = self.base_color
        self.fitness = 0.0
        self.obstacles_passed = 0

        self._anim_state = "run"
        self._anim_frame = 0      # frame atual dentro da animação
        self._anim_tick = 0       # contador de ticks de jogo

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def jump(self):
        if self.alive and self.on_ground and not self.ducking:
            self.vy = JUMP_VELOCITY
            self.on_ground = False

    def duck(self, active: bool):
        if not self.alive or not self.on_ground:
            self.ducking = False
            self.height = RUN_HEIGHT
            return
        self.ducking = active
        new_h = DUCK_HEIGHT if active else RUN_HEIGHT
        if new_h != self.height:
            self.y += (self.height - new_h)
            self.height = new_h

    def update(self):
        if not self.alive:
            self._advance_anim()
            return
        self.vy += GRAVITY
        self.y += self.vy
        if self.y + self.height >= config.GROUND_Y:
            self.y = config.GROUND_Y - self.height
            self.vy = 0
            self.on_ground = True
        if self.ducking:
            self._set_anim("duck")
        elif not self.on_ground:
            self._set_anim("jump")
        else:
            self._set_anim("run")
        self._advance_anim()

    def kill(self):
        if self.alive:
            self.alive = False
            self._set_anim("dead", reset=True)

    def _set_anim(self, state: str, reset: bool = False):
        if state != self._anim_state or reset:
            self._anim_state = state
            self._anim_frame = 0
            self._anim_tick = 0

    def _advance_anim(self):
        self._anim_tick += 1
        tick_rate = ANIM_TICK.get(self._anim_state, 5)
        if self._anim_tick >= tick_rate:
            self._anim_tick = 0
            frames = self._current_frames()
            if not frames:
                return
            if self._anim_state == "dead":
                # trava no último frame em vez de fazer loop
                self._anim_frame = min(self._anim_frame + 1, len(frames) - 1)
            else:
                self._anim_frame = (self._anim_frame + 1) % len(frames)

    def _current_frames(self) -> list[pygame.Surface]:
        folder, prefix = _ANIM_SOURCES.get(self._anim_state, ("dino", "Run"))
        size = (SPRITE_W, DUCK_SPRITE_H if self.ducking else SPRITE_H)
        if self.base_color != COLOR_ALIVE:
            return assets.get_animation_tinted(folder, prefix, size, self.base_color)
        return assets.get_animation(folder, prefix, size)

    def _current_sprite(self) -> pygame.Surface | None:
        frames = self._current_frames()
        if not frames:
            return None
        return frames[min(self._anim_frame, len(frames) - 1)]

    def _sprite_blit_pos(self) -> tuple[int, int]:
        """Centraliza horizontalmente e alinha pés do sprite com base do hitbox."""
        sprite_h = DUCK_SPRITE_H if self.ducking else SPRITE_H
        bx = int(self.x) - (SPRITE_W - self.width) // 2
        by = int(self.y) + self.height - sprite_h
        return bx, by

    def draw(self, surface: pygame.Surface, ghost: bool = False):
        sprite = self._current_sprite()

        if ghost:
            if sprite is not None:
                s = sprite.copy()
                s.set_alpha(GHOST_ALPHA)
                surface.blit(s, self._sprite_blit_pos())
            else:
                s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                s.fill((*self.base_color, GHOST_ALPHA))
                pygame.draw.line(s, (255, 60, 60, GHOST_ALPHA + 30), (6, 6), (self.width - 6, self.height - 6), 2)
                pygame.draw.line(s, (255, 60, 60, GHOST_ALPHA + 30), (6, self.height - 6), (self.width - 6, 6), 2)
                surface.blit(s, (int(self.x), int(self.y)))
            return

        if sprite is not None:
            surface.blit(sprite, self._sprite_blit_pos())
        else:
            pygame.draw.rect(surface, self.color, self.rect)
            pygame.draw.rect(surface, (20, 20, 30), self.rect, 1)
            eye_x = int(self.x) + self.width - 8
            eye_y = int(self.y) + 6
            pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), 3)
            pygame.draw.circle(surface, (20, 20, 30), (eye_x, eye_y), 1)

