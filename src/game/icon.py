"""Ícone da janela: carrega de assets/icon.png se existir, senão desenha procedural."""
from pathlib import Path
import pygame
from src import config

ICON_PATH = config.ROOT / "assets" / "icon.png"


def _procedural() -> pygame.Surface:
    """Mini dino estilizado, 64x64, no mesmo espírito do sprite do jogo."""
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    body = (60, 60, 60)
    eye_white = (255, 255, 255)
    eye_pupil = (20, 20, 30)
    contour = (20, 20, 30)

    pygame.draw.rect(s, body, pygame.Rect(14, 18, 36, 38), border_radius=4)
    pygame.draw.rect(s, contour, pygame.Rect(14, 18, 36, 38), width=2, border_radius=4)
    pygame.draw.rect(s, body, pygame.Rect(34, 8, 22, 18), border_radius=3)
    pygame.draw.rect(s, contour, pygame.Rect(34, 8, 22, 18), width=2, border_radius=3)
    pygame.draw.circle(s, eye_white, (49, 16), 4)
    pygame.draw.circle(s, eye_pupil, (50, 16), 2)
    pygame.draw.rect(s, body, pygame.Rect(18, 54, 8, 8))
    pygame.draw.rect(s, body, pygame.Rect(36, 54, 8, 8))
    return s


def load() -> pygame.Surface:
    if ICON_PATH.exists():
        try:
            return pygame.image.load(str(ICON_PATH)).convert_alpha()
        except Exception:
            pass
    return _procedural()


def apply():
    """Define o ícone da janela atual. Chamar antes ou logo após set_mode()."""
    pygame.display.set_icon(load())
