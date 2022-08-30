from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import time

import pygame as pg
from pygame import font, SRCALPHA, BLEND_RGBA_MIN
from math import floor

from pygame.surface import Surface
from pygame.rect import Rect

from ..conf import Conf

if TYPE_CHECKING:
    from ..app import App

from ..app import State

ROOT_DIR = Conf.ROOT_DIR


class SongSelect(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        # 0 => ド屑
        # 1 => ゴーストルール
        # などなど
        self.song_idx = 0
        self.song_ref = self.ctx.song_cache[self.ctx.song_names[self.song_idx]]

        self.bg: Surface = self.ctx.image_cache["assets/menu_tint.jpg"]
        self.bg = pg.transform.scale(self.bg, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.overlay = pg.Surface((self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT))
        self.overlay.set_alpha(128)
        self.overlay.fill((0, 0, 0))

        self.frame: Surface = self.ctx.image_cache["assets/frame90.jpg"]

        scale = self.ctx.SCREEN_WIDTH * 0.6 / self.frame.get_width()
        self.frame = pg.transform.scale(
            self.frame, (self.frame.get_width() * scale, self.frame.get_height() * scale)
        ).convert_alpha()
        self.frame_rect = self.frame.get_rect(center=self.ctx.Display.get_rect().center)
        self.frame_rect.y = self.ctx.SCREEN_HEIGHT // 7

        self.frame.set_alpha(255)

        self.lite_img = self.load_lite_img()
        self.prev_img: Optional[Surface] = None

        self.rmap_button = self.ctx.image_cache["assets/switch_button_1_crop.jpg"]
        scale = self.ctx.SCREEN_WIDTH * 0.05 / self.rmap_button.get_width()

        # Blue on top, purple on bottom
        self.rmap_button = pg.transform.flip(
            pg.transform.scale(
                self.rmap_button, (self.rmap_button.get_width() * scale, self.rmap_button.get_height() * scale)
            ),
            flip_x=False,
            flip_y=True,
        ).convert_alpha()
        self.rmap_button_rect = self.rmap_button.get_rect()
        self.rmap_button_rect.x = self.ctx.SCREEN_WIDTH // 10 * 9 - self.rmap_button_rect.width
        self.rmap_button_rect.centery = self.frame_rect.centery

        self.lmap_button = self.ctx.image_cache["assets/switch_button_1_crop.jpg"]

        self.lmap_button = pg.transform.flip(
            pg.transform.scale(
                self.lmap_button, (self.lmap_button.get_width() * scale, self.lmap_button.get_height() * scale)
            ),
            flip_x=True,
            flip_y=True,
        ).convert_alpha()
        self.lmap_button_rect = self.lmap_button.get_rect()
        self.lmap_button_rect.x = self.ctx.SCREEN_WIDTH // 10
        self.lmap_button_rect.centery = self.frame_rect.centery

        self.info_button = self.ctx.image_cache["assets/info_icon.jpg"]
        scale = self.ctx.SCREEN_WIDTH * 0.05 / self.info_button.get_width()
        self.info_button = pg.transform.scale(
            self.info_button, (self.info_button.get_width() * scale, self.info_button.get_height() * scale)
        ).convert_alpha()
        self.info_button_rect = self.info_button.get_rect(center=self.ctx.Display.get_rect().center)
        self.info_button_rect.y = self.ctx.SCREEN_HEIGHT // 10 * 7
        self.info_button_rect.x = self.frame_rect.x + self.info_button_rect.width // 5 * 4

        self.info_overlay = Surface((self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT))
        self.info_overlay.set_alpha(0)
        self.info_overlay.fill((0, 0, 0))

        self.info_pad = self.ctx.image_cache["assets/info_pad.jpg"]
        self.info_pad = pg.transform.scale(self.info_pad, (0, 0)).convert_alpha()
        self.info_pad_rect = self.info_pad.get_rect(center=self.ctx.Display.get_rect().center)

        font_scale = 20
        self.font = font.Font(f"{ROOT_DIR}/fonts/KozGoPro-Bold.otf", self.ctx.SCREEN_HEIGHT // font_scale)
        self.song_text = self.font.render(f"【{self.song_ref.prod}】{self.song_ref.name}", True, (255, 255, 255))
        self.song_text.set_alpha(200)
        self.song_text_rect = self.song_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.song_text_rect.centery = self.info_button_rect.centery

        # INFO THINGS
        self.info_font = font.Font(f"{ROOT_DIR}/fonts/KozGoPro-Bold.otf", 0)
        self.info_song_text = self.info_font.render("", True, (255, 255, 255))
        self.info_song_text_rect = self.info_pad.get_rect().center
        self.info_prod_text = self.info_font.render("", True, (255, 255, 255))
        self.info_prod_text_rect = self.info_pad.get_rect().center
        self.info_labels_text = self.info_font.render("", True, (255, 255, 255))
        self.info_labels_text_rect = self.info_pad.get_rect().center
        self.info_cover = Surface((0, 0), SRCALPHA)
        self.info_cover_rect = self.info_pad.get_rect().center
        self.info_vocaloid = Surface((0, 0), SRCALPHA)
        self.info_vocaloid_rect = self.info_pad.get_rect().center
        self.info_cover_text = self.info_font.render("", True, (255, 255, 255))
        self.info_cover_text_rect = self.info_pad.get_rect().center
        self.info_vocaloid_text = self.info_font.render("", True, (255, 255, 255))
        self.info_vocaloid_text_rect = self.info_pad.get_rect().center
        self.info_disclaimer = self.info_font.render("", True, (255, 255, 255))
        self.info_disclaimer_rect = self.info_pad.get_rect().center

        self.hover_right = False
        self.hover_left = False
        self.hover_info = True
        self.hover_out = False

        self.phase_info = False
        self.unphase_info = False
        self.showing_info = False
        self.pad_zoom_scale = 0
        self.info_font_scale = 100
        self.info_avatar_scale = 0

        self.switching = False
        self.switching_left = False

        self.prev_percent: int = 0

    def load_lite_img(self) -> Surface:
        scale = self.ctx.SCREEN_WIDTH * 0.6 / self.ctx.image_cache["assets/frame90.jpg"].get_width()
        img = self.ctx.image_cache[self.song_ref.lite_img]

        img = pg.transform.scale(img, (img.get_width() * scale, img.get_height() * scale)).convert_alpha()

        img.set_alpha(250)
        return img

    def switch_map(self) -> None:
        self.switching = True

        # When the index reaches either end of the list, go to the other end
        if self.hover_right:
            self.song_idx += 1
            self.rmap_button.set_alpha(255)
            if self.song_idx >= len(self.ctx.song_names):
                self.song_idx = 0

        elif self.hover_left:
            self.song_idx -= 1
            self.lmap_button.set_alpha(255)
            if self.song_idx < 0:
                self.song_idx = len(self.ctx.song_names) - 1
            self.switching_left = True

        self.hover_right = False
        self.hover_left = False

        self.prev_img = self.lite_img
        self.song_ref = self.ctx.song_cache[self.ctx.song_names[self.song_idx]]
        self.lite_img = self.load_lite_img()

        self.song_text = self.font.render(f"【{self.song_ref.prod}】{self.song_ref.name}", True, (255, 255, 255))
        self.song_text.set_alpha(200)
        self.song_text_rect = self.song_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.song_text_rect.centery = self.info_button_rect.centery

        # Change the previewing song
        self.ctx.mixer.load(f"{ROOT_DIR}/{self.song_ref.lite_song_path}")
        time.sleep(0.2)
        self.ctx.mixer.set_volume(0.4)
        self.ctx.mixer.play()

        self.prev_percent = 100

    def show_info(self) -> None:
        self.phase_info = True
        self.hover_info = False
        self.info_button.set_alpha(255)

    def hide_info(self) -> None:
        self.unphase_info = True
        self.hover_out = False

    def animate_info(self) -> None:
        if self.phase_info:
            if self.info_overlay.get_alpha() >= 200:  # type: ignore
                self.phase_info = False
                self.showing_info = True
                return
        elif self.unphase_info:
            if self.info_overlay.get_alpha() <= 0:  # type: ignore
                self.unphase_info = False
                self.showing_info = False

                self.pad_zoom_scale = 0
                self.info_font_scale = 100
                self.info_avatar_scale = 0
                return

        if self.phase_info:
            self.info_overlay.set_alpha(self.info_overlay.get_alpha() + 10)  # type: ignore
        elif self.unphase_info:
            self.info_overlay.set_alpha(self.info_overlay.get_alpha() - 10)  # type: ignore

        self.info_pad = self.ctx.image_cache["assets/info_pad.jpg"]
        scale = self.ctx.SCREEN_WIDTH * self.pad_zoom_scale / self.info_pad.get_width()

        self.info_pad = pg.transform.scale(
            self.info_pad, (self.info_pad.get_width() * scale, self.info_pad.get_height() * scale)
        ).convert_alpha()
        self.info_pad_rect = self.info_pad.get_rect(center=self.ctx.Display.get_rect().center)

        if self.pad_zoom_scale >= 0.1:
            # Render things on the pad
            self.info_font = font.Font(
                f"{ROOT_DIR}/fonts/SourceHanSerif-Bold.otf", floor(self.ctx.SCREEN_HEIGHT / self.info_font_scale)
            )

            self.info_song_text = self.info_font.render("Song Name: " + self.song_ref.name, True, (50, 50, 50))
            self.info_song_text_rect = self.info_song_text.get_rect()
            self.info_song_text_rect.centerx = self.info_pad_rect.centerx
            self.info_song_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height / 8 * 1)

            self.info_prod_text = self.info_font.render("Producer: " + self.song_ref.prod, True, (50, 50, 50))
            self.info_prod_text_rect = self.info_prod_text.get_rect()
            self.info_prod_text_rect.centerx = self.info_pad_rect.centerx
            self.info_prod_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 1.5)

            self.info_labels_text = self.info_font.render("【C. Vocal】    【Vocaloid】", True, (50, 50, 50))
            self.info_labels_text_rect = self.info_labels_text.get_rect()
            self.info_labels_text_rect.centerx = self.info_pad_rect.centerx
            self.info_labels_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height / 8 * 2.5)

            raw_img = self.ctx.image_cache[self.song_ref.vocals.cover_avatar]
            raw_img = pg.transform.scale(raw_img, (self.info_avatar_scale, self.info_avatar_scale)).convert_alpha()
            self.info_cover = Surface(raw_img.get_size(), SRCALPHA)
            pg.draw.ellipse(self.info_cover, (255, 255, 255, 255), (0, 0, raw_img.get_width(), raw_img.get_height()))
            self.info_cover.blit(raw_img, (0, 0), special_flags=BLEND_RGBA_MIN)
            self.info_cover_rect = self.info_cover.get_rect()
            self.info_cover_rect.centerx = floor(self.info_pad_rect.centerx - self.info_pad_rect.width // 8 * 1.5)
            self.info_cover_rect.centery = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 4.25)

            raw_img = self.ctx.image_cache[self.song_ref.vocals.vocaloid_avatar]
            raw_img = pg.transform.scale(raw_img, (self.info_avatar_scale, self.info_avatar_scale)).convert_alpha()
            self.info_vocaloid = Surface(raw_img.get_size(), SRCALPHA)
            pg.draw.ellipse(self.info_vocaloid, (255, 255, 255, 255), (0, 0, raw_img.get_width(), raw_img.get_height()))
            self.info_vocaloid.blit(raw_img, (0, 0), special_flags=BLEND_RGBA_MIN)
            self.info_vocaloid_rect = self.info_vocaloid.get_rect()
            self.info_vocaloid_rect.centerx = floor(self.info_pad_rect.centerx + self.info_pad_rect.width // 8 * 1.5)
            self.info_vocaloid_rect.centery = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 4.25)

            self.info_cover_text = self.info_font.render(
                f"{self.song_ref.vocals.cover == '' and 'None' or self.song_ref.vocals.cover}",
                True,
                (50, 50, 50),
            )
            self.info_cover_text_rect = self.info_cover_text.get_rect()
            self.info_cover_text_rect.centerx = self.info_cover_rect.centerx
            self.info_cover_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height / 8 * 5.5)

            self.info_vocaloid_text = self.info_font.render(
                self.song_ref.vocals.vocaloid,
                True,
                (50, 50, 50),
            )
            self.info_vocaloid_text_rect = self.info_vocaloid_text.get_rect()
            self.info_vocaloid_text_rect.centerx = self.info_vocaloid_rect.centerx
            self.info_vocaloid_text_rect.y = self.info_cover_text_rect.y

            self.info_disclaimer = self.info_font.render(
                self.song_ref.questionable and "* Contains questionable lyrics" or "",
                True,
                (255, 102, 128),
            )
            self.info_disclaimer_rect = self.info_disclaimer.get_rect()
            self.info_disclaimer_rect.x = self.info_pad_rect.left + self.info_pad_rect.width // 8
            self.info_disclaimer_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height / 8 * 6.5)
        else:
            self.info_song_text = Surface((0, 0), SRCALPHA)
            self.info_song_text_rect = Rect(0, 0, 0, 0)
            self.info_prod_text = Surface((0, 0), SRCALPHA)
            self.info_prod_text_rect = Rect(0, 0, 0, 0)
            self.info_labels_text = Surface((0, 0), SRCALPHA)
            self.info_labels_text_rect = Rect(0, 0, 0, 0)
            self.info_cover = Surface((0, 0), SRCALPHA)
            self.info_cover_rect = Rect(0, 0, 0, 0)
            self.info_vocaloid = Surface((0, 0), SRCALPHA)
            self.info_vocaloid_rect = Rect(0, 0, 0, 0)
            self.info_cover_text = Surface((0, 0), SRCALPHA)
            self.info_cover_text_rect = Rect(0, 0, 0, 0)
            self.info_vocaloid_text = Surface((0, 0), SRCALPHA)
            self.info_vocaloid_text_rect = Rect(0, 0, 0, 0)
            self.info_disclaimer = Surface((0, 0), SRCALPHA)
            self.info_disclaimer_rect = Rect(0, 0, 0, 0)

        if self.phase_info:
            self.pad_zoom_scale += 0.4 / 20
            self.info_font_scale -= 75 / 20
            self.info_avatar_scale += (self.ctx.SCREEN_HEIGHT / 6.75) / 20
        elif self.unphase_info:
            self.pad_zoom_scale -= 0.4 / 20
            self.info_font_scale += 75 / 20
            self.info_avatar_scale -= (self.ctx.SCREEN_HEIGHT / 6.75) / 20

    def update(self) -> None:
        # Loop the preview music
        music_pos = self.ctx.mixer.get_music_pos()
        if music_pos == -1:
            self.ctx.mixer.load(f"{ROOT_DIR}/{self.song_ref.lite_song_path}")
            self.ctx.mixer.set_volume(0.4)
            self.ctx.mixer.play()

        cursor = pg.mouse.get_pos()

        if self.switching:
            if self.prev_percent <= 0:
                self.switching = False
                self.switching_left = False
                self.prev_img = None
                return

            # Fast to slow wipe effect
            if self.prev_percent > 40:
                self.prev_percent -= 8
            elif self.prev_percent > 25:
                self.prev_percent -= 3
            elif self.prev_percent > 0:
                self.prev_percent -= 1

        elif self.phase_info or self.unphase_info:
            self.animate_info()

        elif self.showing_info:
            x, y = cursor

            # Checks:
            # 1. The cursor is not within the pad Rect
            # 2. But it's ok if the cursor is on a pixel on the pad Rect that has an alpha value of 0
            if (
                not self.info_pad_rect.collidepoint(x, y)
                or self.info_pad.get_at([x - self.info_pad_rect.x, y - self.info_pad_rect.y])[3] == 0
            ):
                self.hover_out = True
            else:
                self.hover_out = False

        else:
            match cursor:
                # Checks:
                # 1. The cursor is within the Surface Rect
                # 2. The cursor is not on a pixel of the Surface that has an alpha value of 0
                case (
                    x,
                    y,
                ) if self.rmap_button_rect.left < x < self.rmap_button_rect.right and self.rmap_button_rect.top < y < self.rmap_button_rect.bottom and (
                    self.rmap_button.get_at([x - self.rmap_button_rect.x, y - self.rmap_button_rect.y])[3] > 0
                ):
                    self.rmap_button.set_alpha(100)
                    self.hover_right = True
                case (
                    x,
                    y,
                ) if self.lmap_button_rect.left < x < self.lmap_button_rect.right and self.lmap_button_rect.top < y < self.lmap_button_rect.bottom and (
                    self.lmap_button.get_at([x - self.lmap_button_rect.x, y - self.lmap_button_rect.y])[3] > 0
                ):
                    self.lmap_button.set_alpha(100)
                    self.hover_left = True
                case (
                    x,
                    y,
                ) if self.info_button_rect.left < x < self.info_button_rect.right and self.info_button_rect.top < y < self.info_button_rect.bottom and (
                    self.info_button.get_at([x - self.info_button_rect.x, y - self.info_button_rect.y])[3] > 0
                ):
                    self.info_button.set_alpha(100)
                    self.hover_info = True

                case _:
                    self.rmap_button.set_alpha(255)
                    self.lmap_button.set_alpha(255)
                    self.info_button.set_alpha(255)
                    self.hover_right = False
                    self.hover_left = False
                    self.hover_info = False

    def draw(self) -> None:
        self.ctx.Display.blit(self.bg, (0, 0))
        self.ctx.Display.blit(self.overlay, (0, 0))
        self.ctx.Display.blit(self.rmap_button, self.rmap_button_rect)
        self.ctx.Display.blit(self.lmap_button, self.lmap_button_rect)
        self.ctx.Display.blit(self.info_button, self.info_button_rect)
        self.ctx.Display.blit(self.song_text, self.song_text_rect)

        if self.prev_img:
            # Gradually draw the next song's lite_img over the old one
            part_img = Surface.copy(self.lite_img)
            pixels_removed_b = part_img.get_width() * self.prev_percent / 100

            for w in range(floor(pixels_removed_b)):
                for h in range(part_img.get_height()):
                    part_img.set_at((self.switching_left and part_img.get_width() - w or w, h), (255, 255, 255, 0))

            self.ctx.Display.blit(self.prev_img, self.frame_rect)
            self.ctx.Display.blit(part_img, self.frame_rect)

            self.ctx.Display.blit(self.frame, self.frame_rect)
        else:
            # Normal
            self.ctx.Display.blit(self.lite_img, (self.frame_rect.x, self.frame_rect.y))
            self.ctx.Display.blit(self.frame, self.frame_rect)

        if self.phase_info or self.showing_info:
            self.ctx.Display.blit(self.info_overlay, (0, 0))
            self.ctx.Display.blit(self.info_pad, self.info_pad_rect)
            self.ctx.Display.blit(self.info_song_text, self.info_song_text_rect)
            self.ctx.Display.blit(self.info_prod_text, self.info_prod_text_rect)
            self.ctx.Display.blit(self.info_labels_text, self.info_labels_text_rect)
            self.ctx.Display.blit(self.info_cover_text, self.info_cover_text_rect)
            self.ctx.Display.blit(self.info_vocaloid_text, self.info_vocaloid_text_rect)
            self.ctx.Display.blit(self.info_disclaimer, self.info_disclaimer_rect)
            self.ctx.Display.blit(self.info_cover, self.info_cover_rect)
            self.ctx.Display.blit(self.info_vocaloid, self.info_vocaloid_rect)
