from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Tuple

if TYPE_CHECKING:
    from ..app import App

import pygame as pg
from pygame import font
from math import floor

from ..app import State


class Loading(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg = (0, 0, 0)

        self.progress = 0

        self.loading_bar_rect = pg.Rect(0, 0, self.ctx.SCREEN_WIDTH / 2, self.ctx.SCREEN_HEIGHT / 8)
        self.loading_bar_rect.center = self.ctx.Display.get_rect().center

        self.progress_rect = pg.Rect(0, 0, 0, self.loading_bar_rect.height - 10)
        self.progress_rect.x = self.loading_bar_rect.x + 5
        self.progress_rect.centery = self.loading_bar_rect.centery

        font_size = self.ctx.SCREEN_HEIGHT // 18
        self.font = font.SysFont("Monospace", font_size)
        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

    def update(self) -> None:
        self.progress_rect.width = floor(self.loading_bar_rect.width * self.progress / 100) - 10

        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

    def draw(self) -> None:
        self.ctx.Display.fill(self.bg)
        pg.draw.rect(self.ctx.Display, (121, 183, 172), self.loading_bar_rect, 5)
        pg.draw.rect(self.ctx.Display, (161, 223, 212), self.progress_rect)

        # Scale is used for responsive UI
        text_pos_scale = 14
        self.ctx.Display.blit(
            self.progress_surface,
            (
                self.progress_rect.right - self.progress_surface.get_width() / 2,
                self.progress_rect.top - self.ctx.SCREEN_HEIGHT / text_pos_scale,
            ),
        )

    def load_task(self, func: Callable[..., Tuple[int, int]], *args) -> bool:
        """
        Returns:
        |   True => Complete; now do something e.g. switch States
        |   False => Incomplete; will continue loading next tick
        """
        done, total = func(*args)

        self.progress = floor(done / total * 100)

        return done == total
