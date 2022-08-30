from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import App

import pygame as pg
from pygame import font

from pygame.surface import Surface

from pybeats import ROOT_DIR
from ..app import State


class Menu(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg: Surface = self.ctx.image_cache["assets/menu_tint.jpg"]
        self.bg = pg.transform.scale(self.bg, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.overlay = pg.Surface((self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT))
        self.overlay.set_alpha(128)
        self.overlay.fill((0, 0, 0))

        self.title: Surface = pg.image.load(f"{ROOT_DIR}/assets/Pybeats_text.jpg")

        scale = self.ctx.SCREEN_WIDTH * 0.8 / self.title.get_width()

        self.title = pg.transform.scale(
            self.title, (self.title.get_width() * scale, self.title.get_height() * scale)
        ).convert_alpha()

        self.title_rect = self.title.get_rect(center=self.ctx.Display.get_rect().center)
        self.title_rect.y = self.ctx.SCREEN_HEIGHT // 6

        font_scale = 10
        self.font = font.Font(f"{ROOT_DIR}/fonts/Mylodon-Light.otf", self.ctx.SCREEN_HEIGHT // font_scale)

        self.play_text = self.font.render("    Play    ", True, (120, 120, 120))
        self.play_rect = self.play_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.play_rect.y = self.ctx.SCREEN_HEIGHT // 6 * 3

        self.options_text = self.font.render("  Options  ", True, (120, 120, 120))
        self.options_rect = self.options_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.options_rect.y = self.ctx.SCREEN_HEIGHT // 6 * 4

        self.hover_play = False
        self.hover_options = False

        self.prev_hovering = False
        self.hovering = False

        self.switchf = False
        self.shift_dist = self.ctx.SCREEN_HEIGHT // 500
        self.fade_speed = 8

    def update(self) -> None:
        # Background music for menu screen
        if self.ctx.mixer.get_music_pos() == -1:
            self.ctx.mixer.load(f"{ROOT_DIR}/audio/君の夜をくれ.mp3")
            self.ctx.mixer.play()

        if self.switchf:
            self.title_rect.y -= self.shift_dist
            self.play_rect.y -= self.shift_dist
            self.options_rect.y -= self.shift_dist

            self.title.set_alpha(self.title.get_alpha() - self.fade_speed)  # type: ignore
            self.play_text.set_alpha(self.play_text.get_alpha() - self.fade_speed)  # type: ignore
            self.options_text.set_alpha(self.options_text.get_alpha() - self.fade_speed)  # type: ignore
        else:
            cursor = pg.mouse.get_pos()

            match cursor:
                case (
                    x,
                    y,
                ) if self.play_rect.left < x < self.play_rect.right and self.play_rect.top < y < self.play_rect.bottom:
                    self.play_text = self.font.render(">>>   Play   <<<", True, (255, 255, 255))
                    self.hover_play = True
                    self.hover_options = False
                case (
                    x,
                    y,
                ) if self.options_rect.left < x < self.options_rect.right and self.options_rect.top < y < self.options_rect.bottom:
                    self.options_text = self.font.render(">>> Options <<<", True, (255, 255, 255))
                    self.hover_options = True
                    self.hover_play = False
                case _:
                    self.play_text = self.font.render("    Play    ", True, (150, 150, 150))
                    self.options_text = self.font.render("  Options  ", True, (150, 150, 150))
                    self.hover_play = False
                    self.hover_options = False

            self.play_rect = self.play_text.get_rect(center=self.ctx.Display.get_rect().center)
            self.play_rect.y = self.ctx.SCREEN_HEIGHT // 6 * 3
            self.options_rect = self.options_text.get_rect(center=self.ctx.Display.get_rect().center)
            self.options_rect.y = self.ctx.SCREEN_HEIGHT // 6 * 4

            temp = self.hovering
            self.hovering = self.hover_play or self.hover_options
            self.prev_hovering = temp

            if not self.prev_hovering and self.prev_hovering != self.hovering:
                self.ctx.mixer.play_sfx(self.ctx.sfx.tap_lane_trunc)

    def switch(self) -> None:
        self.switchf = True
        self.hover_play = False
        self.ctx.mixer.play_sfx(self.ctx.sfx.play_title)

    def draw(self) -> None:
        self.ctx.Display.blit(self.bg, (0, 0))
        self.ctx.Display.blit(self.overlay, (0, 0))
        self.ctx.Display.blit(self.title, self.title_rect)
        self.ctx.Display.blit(self.play_text, self.play_rect)
        self.ctx.Display.blit(self.options_text, self.options_rect)
