from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg
from pygame.rect import Rect
from pygame.surface import Surface

from ..conf import Conf

if TYPE_CHECKING:
    from ..app import App

from ..app import State

ROOT_DIR = Conf.ROOT_DIR


class InGame(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg: Surface = self.ctx.image_cache["assets/ingame.jpg"]
        self.bg = pg.transform.scale(self.bg, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

    def update(self) -> None:
        return super().update()

    def draw(self) -> None:
        self.ctx.Display.blit(self.bg, (0, 0))
