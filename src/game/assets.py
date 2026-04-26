"""Loader de sprites/animações de assets/ com cache e tint por cor.

Convenção e estrutura completa documentadas em ASSETS.md.
"""
from pathlib import Path
import pygame
from src import config

ASSETS_DIR = config.ROOT / "assets"

_cache: dict[str, pygame.Surface] = {}
_tint_cache: dict[tuple, pygame.Surface] = {}
_anim_cache: dict[tuple, list[pygame.Surface]] = {}


def get(name: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
    """Devolve sprite (escalado se size for dado) ou None se o arquivo não existe."""
    key = f"{name}@{size}" if size else name
    if key in _cache:
        return _cache[key]
    path = ASSETS_DIR / f"{name}.png"
    if not path.exists():
        return None
    try:
        img = pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None
    if size and img.get_size() != size:
        img = pygame.transform.smoothscale(img, size)
    _cache[key] = img
    return img


def get_animation(folder: str, prefix: str, size: tuple[int, int]) -> list[pygame.Surface]:
    """Carrega frames numerados de assets/{folder}/{Prefix} (N).png como uma animação.

    Suporta o padrão de export usual ("Run (1).png", "Run (2).png" …).
    Devolve lista vazia se nenhum frame for encontrado.
    """
    key = (folder, prefix, size)
    if key in _anim_cache:
        return _anim_cache[key]
    base = ASSETS_DIR / folder
    frames: list[pygame.Surface] = []
    if not base.exists():
        _anim_cache[key] = frames
        return frames
    i = 1
    while True:
        path = base / f"{prefix} ({i}).png"
        if not path.exists():
            break
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            if img.get_size() != size:
                img = pygame.transform.smoothscale(img, size)
            frames.append(img)
        except pygame.error:
            break
        i += 1
    _anim_cache[key] = frames
    return frames


def get_animation_tinted(folder: str, prefix: str, size: tuple[int, int],
                         color: tuple[int, int, int]) -> list[pygame.Surface]:
    """Versão colorida de uma animação: grayscale + multiply pela cor.

    Preserva sombras e contornos do sprite original — cada pixel vira a cor
    desejada com a luminosidade do pixel original.
    """
    key = (folder, prefix, size, color, "tinted")
    if key in _anim_cache:
        return _anim_cache[key]
    base = get_animation(folder, prefix, size)
    out: list[pygame.Surface] = []
    for img in base:
        gray = pygame.transform.grayscale(img)
        # clareia antes de multiplicar — sem isso o sprite tintado fica escuro demais
        gray.fill((40, 40, 40, 0), special_flags=pygame.BLEND_RGB_ADD)
        gray.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        out.append(gray)
    _anim_cache[key] = out
    return out


def get_tinted(name: str, size: tuple[int, int], color: tuple[int, int, int]) -> pygame.Surface | None:
    """Versão colorida do sprite — útil pra dar cor única por dino na população."""
    base = get(name, size)
    if base is None:
        return None
    key = (name, size, color)
    if key in _tint_cache:
        return _tint_cache[key]
    tinted = base.copy()
    tinted.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    _tint_cache[key] = tinted
    return tinted
