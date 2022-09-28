from __future__ import annotations

import random
from math import floor
from typing import TYPE_CHECKING, Literal, Optional, Tuple

import pygame as pg
from pygame import BLEND_RGBA_MIN, SRCALPHA, font
from pygame.rect import Rect
from pygame.surface import Surface

from ..conf import Conf
from ..lib import Difficulty

# from PIL import Image


if TYPE_CHECKING:
    from ..app import App

from ..app import State

ROOT_DIR = Conf.ROOT_DIR


class SongSelect(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        if self.ctx.target_map:
            self.song_ref = self.ctx.song_cache[self.ctx.target_map]
        else:
            self.song_idx = random.randint(0, len(self.ctx.song_cache) - 1)
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
        self.frame_rect.y = self.ctx.SCREEN_HEIGHT // 20

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
        self.info_button_rect.bottom = self.frame_rect.bottom + self.info_button_rect.height // 2
        self.info_button_rect.x = self.frame_rect.x + self.info_button_rect.width // 5 * 4

        # DIFFICULTY BUTTONS
        # gray -> not attempted
        # green -> clear
        # pink -> full combo
        # blue/purple -> all perfect
        self.button_easy = self.ctx.image_cache["assets/button_easy.jpg"]
        button_scale = self.frame_rect.width * 0.25 / self.button_easy.get_width()
        self.button_easy = pg.transform.scale(
            self.button_easy,
            (self.button_easy.get_width() * button_scale, self.button_easy.get_height() * button_scale),
        ).convert_alpha()
        self.button_easy_rect = self.button_easy.get_rect(center=self.ctx.Display.get_rect().center)
        self.button_easy_rect.left = self.frame_rect.left
        self.button_easy_rect.y = floor(self.info_button_rect.y + self.info_button_rect.height * 1.8)

        self.button_normal = self.ctx.image_cache["assets/button_normal.jpg"]
        self.button_normal = pg.transform.scale(
            self.button_normal,
            (self.button_normal.get_width() * button_scale, self.button_normal.get_height() * button_scale),
        ).convert_alpha()
        self.button_normal_rect = self.button_normal.get_rect()
        self.button_normal_rect.x = self.button_easy_rect.x + self.button_easy_rect.width
        self.button_normal_rect.y = self.button_easy_rect.y

        self.button_hard = self.ctx.image_cache["assets/button_hard.jpg"]
        self.button_hard = pg.transform.scale(
            self.button_hard,
            (self.button_hard.get_width() * button_scale, self.button_hard.get_height() * button_scale),
        ).convert_alpha()
        self.button_hard_rect = self.button_hard.get_rect()
        self.button_hard_rect.x = self.button_normal_rect.x + self.button_easy_rect.width
        self.button_hard_rect.y = self.button_easy_rect.y

        self.button_master = self.ctx.image_cache["assets/button_master.jpg"]
        self.button_master = pg.transform.scale(
            self.button_master,
            (self.button_master.get_width() * button_scale, self.button_master.get_height() * button_scale),
        ).convert_alpha()
        self.button_master_rect = self.button_master.get_rect()
        self.button_master_rect.x = self.button_hard_rect.x + self.button_easy_rect.width
        self.button_master_rect.y = self.button_easy_rect.y

        df_scale = self.ctx.SCREEN_HEIGHT // 41
        nf_scale = self.ctx.SCREEN_HEIGHT // 18
        self.diff_font = font.Font(f"{ROOT_DIR}/fonts/Mylodon-Light.otf", df_scale)
        self.num_font = font.Font(f"{ROOT_DIR}/fonts/Mylodon-Light.otf", nf_scale)
        self.num_font.set_bold(True)
        self.easy_diff = self.diff_font.render("Easy", True, (255, 255, 255))
        self.easy_diff_rect = self.easy_diff.get_rect(center=self.button_easy_rect.center)
        self.easy_diff_rect.top = self.button_easy_rect.top + self.easy_diff_rect.height // 4
        self.easy_num = self.num_font.render(str(self.song_ref.difficulty.easy), True, (255, 255, 255))
        self.easy_num_rect = self.easy_num.get_rect(center=self.button_easy_rect.center)
        self.easy_num_rect.centery = (self.button_easy_rect.bottom + self.easy_diff_rect.bottom) // 2

        self.normal_diff = self.diff_font.render("Normal", True, (255, 255, 255))
        self.normal_diff_rect = self.normal_diff.get_rect(center=self.button_normal_rect.center)
        self.normal_diff_rect.top = self.button_normal_rect.top + self.normal_diff_rect.height // 4
        self.normal_num = self.num_font.render(str(self.song_ref.difficulty.normal), True, (255, 255, 255))
        self.normal_num_rect = self.normal_num.get_rect(center=self.button_normal_rect.center)
        self.normal_num_rect.centery = (self.button_normal_rect.bottom + self.normal_diff_rect.bottom) // 2

        self.hard_diff = self.diff_font.render("Hard", True, (255, 255, 255))
        self.hard_diff_rect = self.hard_diff.get_rect(center=self.button_hard_rect.center)
        self.hard_diff_rect.top = self.button_hard_rect.top + self.hard_diff_rect.height // 4
        self.hard_num = self.num_font.render(str(self.song_ref.difficulty.hard), True, (255, 255, 255))
        self.hard_num_rect = self.hard_num.get_rect(center=self.button_hard_rect.center)
        self.hard_num_rect.centery = (self.button_hard_rect.bottom + self.hard_diff_rect.bottom) // 2

        self.master_diff = self.diff_font.render("Master", True, (255, 255, 255))
        self.master_diff_rect = self.master_diff.get_rect(center=self.button_master_rect.center)
        self.master_diff_rect.top = self.button_master_rect.top + self.master_diff_rect.height // 4
        self.master_num = self.num_font.render(str(self.song_ref.difficulty.master), True, (255, 255, 255))
        self.master_num_rect = self.master_num.get_rect(center=self.button_master_rect.center)
        self.master_num_rect.centery = (self.button_master_rect.bottom + self.master_diff_rect.bottom) // 2

        self.diff_arrow = self.ctx.image_cache["assets/diff_arrow.jpg"]
        da_scale = self.ctx.SCREEN_WIDTH / 24 / self.diff_arrow.get_width()
        self.diff_arrow = pg.transform.scale(
            self.diff_arrow, (self.diff_arrow.get_width() * da_scale, self.diff_arrow.get_height() * da_scale)
        ).convert_alpha()
        self.diff_arrow_rect = self.diff_arrow.get_rect()
        self.diff_arrow_rect.centerx = self.normal_diff_rect.centerx
        self.diff_arrow_rect.y = self.easy_diff_rect.y - self.easy_diff_rect.height * 2

        self.diamond_easy, self.diamond_easy_rect, self.grade_easy, self.grade_easy_rect = self.load_diamond_and_rank(
            self.song_ref.diamond.easy, self.song_ref.grade.easy, self.button_easy_rect
        )
        (
            self.diamond_normal,
            self.diamond_normal_rect,
            self.grade_normal,
            self.grade_normal_rect,
        ) = self.load_diamond_and_rank(
            self.song_ref.diamond.normal, self.song_ref.grade.normal, self.button_normal_rect
        )
        self.diamond_hard, self.diamond_hard_rect, self.grade_hard, self.grade_hard_rect = self.load_diamond_and_rank(
            self.song_ref.diamond.hard, self.song_ref.grade.hard, self.button_hard_rect
        )
        (
            self.diamond_master,
            self.diamond_master_rect,
            self.grade_master,
            self.grade_master_rect,
        ) = self.load_diamond_and_rank(
            self.song_ref.diamond.master, self.song_ref.grade.master, self.button_master_rect
        )

        self.back_button = self.ctx.image_cache["assets/back_icon.jpg"]
        scale = self.ctx.SCREEN_WIDTH * 0.05 / self.back_button.get_width()
        self.back_button = pg.transform.scale(
            self.back_button, (self.back_button.get_width() * scale, self.back_button.get_height() * scale)
        ).convert_alpha()
        self.back_button_rect = self.back_button.get_rect()
        self.back_button_rect.x = self.back_button_rect.y = 10

        self.info_overlay = Surface((self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT))
        self.info_overlay.set_alpha(0)
        self.info_overlay.fill((0, 0, 0))

        self.info_pad = self.ctx.image_cache["assets/info_pad.jpg"]
        self.info_pad = pg.transform.scale(self.info_pad, (0, 0)).convert_alpha()
        self.info_pad_rect = self.info_pad.get_rect(center=self.ctx.Display.get_rect().center)

        font_scale = 20
        self.font = font.Font(f"{ROOT_DIR}/fonts/KozGoPro-Bold.otf", self.ctx.SCREEN_HEIGHT // font_scale)
        self.song_text = self.font.render(
            f"【{Conf.text == Conf.JP and self.song_ref.prod or self.song_ref.prod_en}】{Conf.text == Conf.JP and self.song_ref.name or self.song_ref.name_en}",
            True,
            (255, 255, 255),
        )
        self.song_text.set_alpha(200)
        self.song_text_rect = self.song_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.song_text_rect.centery = self.info_button_rect.centery

        # INFO THINGS
        self.info_font = font.Font(f"{ROOT_DIR}/fonts/KozGoPro-Bold.otf", 0)
        self.info_song_text = self.info_font.render("", True, (255, 255, 255))
        self.info_song_text_rect = self.info_pad.get_rect().center
        self.info_prod_text = self.info_font.render("", True, (255, 255, 255))
        self.info_prod_text_rect = self.info_pad.get_rect().center
        self.info_vocals_text = self.info_font.render("", True, (255, 255, 255))
        self.info_vocals_text_rect = self.info_pad.get_rect().center
        self.info_mapper_text = self.info_font.render("", True, (255, 255, 255))
        self.info_mapper_text_rect = self.info_pad.get_rect().center
        self.info_avocals = Surface((0, 0), SRCALPHA)
        self.info_avocals_rect = self.info_pad.get_rect().center
        self.info_amapper = Surface((0, 0), SRCALPHA)
        self.info_amapper_rect = self.info_pad.get_rect().center
        self.info_disclaimer = self.info_font.render("", True, (255, 255, 255))
        self.info_disclaimer_rect = self.info_pad.get_rect().center

        self.hover_right = False
        self.hover_left = False
        self.hover_back = False
        self.hover_info = False
        self.hover_out = False
        self.hover_easy = False
        self.hover_normal = False
        self.hover_hard = False
        self.hover_master = False
        self.hover_play = False

        self.difficulty: Difficulty = Difficulty.Normal

        self.back = False
        self.play = False

        self.phase_info = False
        self.unphase_info = False
        self.showing_info = False
        self.pad_zoom_scale = 0
        self.info_font_scale = 110
        self.info_avatar_scale = 0

        self.switching = False
        self.switching_left = False

        self.prev_percent: int = 0

        self.ctx.mixer.unload()
        self.ctx.mixer.load(f"{ROOT_DIR}/{self.song_ref.lite_song_path}")
        self.ctx.mixer.set_volume(0.4)
        self.ctx.mixer.play()

    def load_diamond_and_rank(
        self, grade: Literal["AP", "FC", "CL", "NA"], rank: Literal["C", "B", "A", "S"], button_rect: Rect
    ) -> Tuple[Surface, Rect, Surface, Rect]:

        diamond = self.ctx.image_cache[f"assets/diamond_{grade}.jpg"]
        s = self.ctx.SCREEN_HEIGHT / 18 / diamond.get_height()
        diamond = pg.transform.scale(diamond, (diamond.get_width() * s, diamond.get_height() * s)).convert_alpha()

        match rank:
            case "C":
                colour = (150, 150, 150)
            case "B":
                colour = (70, 150, 120)
            case "A":
                colour = (150, 70, 120)
            case "S":
                colour = (150, 100, 180)

        text = self.num_font.render(rank, True, colour)

        diamond_rect = diamond.get_rect()
        diamond_rect.centerx = button_rect.centerx - button_rect.width // 8
        diamond_rect.y = floor(button_rect.y + button_rect.height * 1.1)

        text_rect = text.get_rect()
        text_rect.centerx = button_rect.centerx + button_rect.width // 8
        text_rect.centery = diamond_rect.centery

        return (diamond, diamond_rect, text, text_rect)

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

        self.song_text = self.font.render(
            f"【{Conf.text == Conf.JP and self.song_ref.prod or self.song_ref.prod_en}】{Conf.text == Conf.JP and self.song_ref.name or self.song_ref.name_en}",
            True,
            (255, 255, 255),
        )
        self.song_text.set_alpha(200)
        self.song_text_rect = self.song_text.get_rect(center=self.ctx.Display.get_rect().center)
        self.song_text_rect.centery = self.info_button_rect.centery

        self.easy_diff = self.diff_font.render("Easy", True, (255, 255, 255))
        self.easy_num = self.num_font.render(str(self.song_ref.difficulty.easy), True, (255, 255, 255))
        self.easy_num_rect = self.easy_num.get_rect(center=self.button_easy_rect.center)
        self.easy_num_rect.centery = (self.button_easy_rect.bottom + self.easy_diff_rect.bottom) // 2
        self.normal_diff = self.diff_font.render("Normal", True, (255, 255, 255))
        self.normal_num = self.num_font.render(str(self.song_ref.difficulty.normal), True, (255, 255, 255))
        self.normal_num_rect = self.normal_num.get_rect(center=self.button_normal_rect.center)
        self.normal_num_rect.centery = (self.button_normal_rect.bottom + self.normal_diff_rect.bottom) // 2
        self.hard_diff = self.diff_font.render("Hard", True, (255, 255, 255))
        self.hard_num = self.num_font.render(str(self.song_ref.difficulty.hard), True, (255, 255, 255))
        self.hard_num_rect = self.hard_num.get_rect(center=self.button_hard_rect.center)
        self.hard_num_rect.centery = (self.button_hard_rect.bottom + self.hard_diff_rect.bottom) // 2
        self.master_diff = self.diff_font.render("Master", True, (255, 255, 255))
        self.master_num = self.num_font.render(str(self.song_ref.difficulty.master), True, (255, 255, 255))
        self.master_num_rect = self.master_num.get_rect(center=self.button_master_rect.center)
        self.master_num_rect.centery = (self.button_master_rect.bottom + self.master_diff_rect.bottom) // 2

        self.diamond_easy, self.diamond_easy_rect, self.grade_easy, self.grade_easy_rect = self.load_diamond_and_rank(
            self.song_ref.diamond.easy, self.song_ref.grade.easy, self.button_easy_rect
        )
        (
            self.diamond_normal,
            self.diamond_normal_rect,
            self.grade_normal,
            self.grade_normal_rect,
        ) = self.load_diamond_and_rank(
            self.song_ref.diamond.normal, self.song_ref.grade.normal, self.button_normal_rect
        )
        self.diamond_hard, self.diamond_hard_rect, self.grade_hard, self.grade_hard_rect = self.load_diamond_and_rank(
            self.song_ref.diamond.hard, self.song_ref.grade.hard, self.button_hard_rect
        )
        (
            self.diamond_master,
            self.diamond_master_rect,
            self.grade_master,
            self.grade_master_rect,
        ) = self.load_diamond_and_rank(
            self.song_ref.diamond.master, self.song_ref.grade.master, self.button_master_rect
        )

        # Change the previewing song
        self.ctx.mixer.load(f"{ROOT_DIR}/{self.song_ref.lite_song_path}")
        self.ctx.mixer.set_volume(0.4)
        self.ctx.mixer.play()

        self.prev_percent = 100

    def switch_difficulty(self) -> None:
        if self.hover_easy:
            self.diff_arrow_rect.centerx = self.easy_diff_rect.centerx
            self.difficulty = Difficulty.Easy
        elif self.hover_normal:
            self.diff_arrow_rect.centerx = self.normal_diff_rect.centerx
            self.difficulty = Difficulty.Normal
        elif self.hover_hard:
            self.diff_arrow_rect.centerx = self.hard_diff_rect.centerx
            self.difficulty = Difficulty.Hard
        elif self.hover_master:
            self.diff_arrow_rect.centerx = self.master_diff_rect.centerx
            self.difficulty = Difficulty.Master

        self.ctx.mixer.play_sfx(self.ctx.sfx.tap_lane_trunc)

    def show_info(self) -> None:
        self.phase_info = True
        self.hover_info = False
        self.info_button.set_alpha(255)

    def hide_info(self) -> None:
        self.unphase_info = True
        self.hover_out = False

    def animate_info(self) -> None:
        if self.phase_info:
            if self.info_overlay.get_alpha() >= 220:  # type: ignore
                self.phase_info = False
                self.showing_info = True
                return
        elif self.unphase_info:
            if self.info_overlay.get_alpha() <= 0:  # type: ignore
                self.unphase_info = False
                self.showing_info = False

                self.pad_zoom_scale = 0
                self.info_font_scale = 110
                self.info_avatar_scale = 0
                return

        if self.phase_info:
            self.info_overlay.set_alpha(self.info_overlay.get_alpha() + 11)  # type: ignore
        elif self.unphase_info:
            self.info_overlay.set_alpha(self.info_overlay.get_alpha() - 11)  # type: ignore

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

            self.info_song_text = self.info_font.render(
                Conf.text.song_name + (Conf.text == Conf.JP and self.song_ref.name or self.song_ref.name_en),
                True,
                (50, 50, 50),
            )
            self.info_song_text_rect = self.info_song_text.get_rect()
            self.info_song_text_rect.left = floor(self.info_pad_rect.left + self.info_pad_rect.width / 10)
            self.info_song_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height / 8 * 1.2)

            self.info_prod_text = self.info_font.render(
                Conf.text.prod + (Conf.text == Conf.JP and self.song_ref.prod or self.song_ref.prod_en),
                True,
                (50, 50, 50),
            )
            self.info_prod_text_rect = self.info_prod_text.get_rect()
            self.info_prod_text_rect.left = self.info_song_text_rect.left
            self.info_prod_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 1.7)

            self.info_vocals_text = self.info_font.render(
                Conf.text.vocals + (Conf.text == Conf.JP and self.song_ref.vocals or self.song_ref.vocals_en),
                True,
                (50, 50, 50),
            )
            self.info_vocals_text_rect = self.info_vocals_text.get_rect()
            self.info_vocals_text_rect.left = self.info_song_text_rect.left
            self.info_vocals_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 2.6)

            self.info_mapper_text = self.info_font.render(Conf.text.mapper + self.song_ref.mapper, True, (50, 50, 50))
            self.info_mapper_text_rect = self.info_mapper_text.get_rect()
            self.info_mapper_text_rect.left = self.info_song_text_rect.left
            self.info_mapper_text_rect.y = floor(self.info_pad_rect.top + self.info_pad_rect.height // 8 * 4.5)

            raw_img = self.ctx.image_cache[self.song_ref.vocals_avatar]
            raw_img = pg.transform.scale(raw_img, (self.info_avatar_scale, self.info_avatar_scale)).convert_alpha()
            self.info_avocals = Surface(raw_img.get_size(), SRCALPHA)
            pg.draw.ellipse(self.info_avocals, (255, 255, 255, 255), (0, 0, raw_img.get_width(), raw_img.get_height()))
            self.info_avocals.blit(raw_img, (0, 0), special_flags=BLEND_RGBA_MIN)
            self.info_avocals_rect = self.info_avocals.get_rect()
            self.info_avocals_rect.right = floor(self.info_pad_rect.right - self.info_pad_rect.width / 10)
            self.info_avocals_rect.centery = self.info_vocals_text_rect.centery

            raw_img = self.ctx.image_cache[f"beatmaps/{self.song_ref.image_name}/images/mapper_avatar.jpg"]
            raw_img = pg.transform.scale(raw_img, (self.info_avatar_scale, self.info_avatar_scale)).convert_alpha()
            self.info_amapper = Surface(raw_img.get_size(), SRCALPHA)
            pg.draw.ellipse(self.info_amapper, (255, 255, 255, 255), (0, 0, raw_img.get_width(), raw_img.get_height()))
            self.info_amapper.blit(raw_img, (0, 0), special_flags=BLEND_RGBA_MIN)
            self.info_amapper_rect = self.info_amapper.get_rect()
            self.info_amapper_rect.right = floor(self.info_pad_rect.right - self.info_pad_rect.width / 10)
            self.info_amapper_rect.centery = self.info_mapper_text_rect.centery

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
            self.info_vocals_text = Surface((0, 0), SRCALPHA)
            self.info_vocals_text_rect = Rect(0, 0, 0, 0)
            self.info_mapper_text = Surface((0, 0), SRCALPHA)
            self.info_mapper_text_rect = Rect(0, 0, 0, 0)
            self.info_avocals = Surface((0, 0), SRCALPHA)
            self.info_avocals_rect = Rect(0, 0, 0, 0)
            self.info_amapper = Surface((0, 0), SRCALPHA)
            self.info_amapper_rect = Rect(0, 0, 0, 0)
            self.info_disclaimer = Surface((0, 0), SRCALPHA)
            self.info_disclaimer_rect = Rect(0, 0, 0, 0)

        if self.phase_info:
            self.pad_zoom_scale += 0.4 / 20
            self.info_font_scale -= 75 / 20
            self.info_avatar_scale += (self.ctx.SCREEN_HEIGHT / 6.75) / 22
        elif self.unphase_info:
            self.pad_zoom_scale -= 0.4 / 20
            self.info_font_scale += 75 / 20
            self.info_avatar_scale -= (self.ctx.SCREEN_HEIGHT / 6.75) / 22

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
                ) if self.back_button_rect.left < x < self.back_button_rect.right and self.back_button_rect.top < y < self.back_button_rect.bottom and (
                    self.back_button.get_at([x - self.back_button_rect.x, y - self.back_button_rect.y])[3] > 0
                ) and not self.play:
                    self.back_button.set_alpha(100)
                    self.hover_back = True
                case (
                    x,
                    y,
                ) if self.info_button_rect.left < x < self.info_button_rect.right and self.info_button_rect.top < y < self.info_button_rect.bottom and (
                    self.info_button.get_at([x - self.info_button_rect.x, y - self.info_button_rect.y])[3] > 0
                ):
                    self.info_button.set_alpha(100)
                    self.hover_info = True
                # Thumbnail
                case (
                    x,
                    y,
                ) if self.frame_rect.left < x < self.frame_rect.right and self.frame_rect.top < y < self.frame_rect.bottom and (
                    self.lite_img.get_at([x - self.frame_rect.x, y - self.frame_rect.y])[3] > 0
                ) and not self.back:
                    self.lite_img = self.load_lite_img()

                    if self.difficulty == Difficulty.Easy:
                        self.lite_img.fill((0, 50, 30), special_flags=pg.BLEND_ADD)
                    elif self.difficulty == Difficulty.Normal:
                        self.lite_img.fill((0, 30, 50), special_flags=pg.BLEND_ADD)
                    elif self.difficulty == Difficulty.Hard:
                        self.lite_img.fill((50, 0, 30), special_flags=pg.BLEND_ADD)
                    elif self.difficulty == Difficulty.Master:
                        self.lite_img.fill((30, 0, 50), special_flags=pg.BLEND_ADD)

                    self.hover_play = True
                # Difficulty buttons
                case (
                    x,
                    y,
                ) if self.button_easy_rect.left < x < self.button_easy_rect.right and self.button_easy_rect.top < y < self.button_easy_rect.bottom:
                    self.button_easy.set_alpha(100)
                    self.easy_diff.set_alpha(100)
                    self.easy_num.set_alpha(100)
                    self.hover_easy = True
                    self.hover_normal = False
                    self.hover_hard = False
                    self.hover_master = False
                    self.button_normal.set_alpha(255)
                    self.normal_diff.set_alpha(255)
                    self.normal_num.set_alpha(255)
                    self.button_hard.set_alpha(255)
                    self.hard_diff.set_alpha(255)
                    self.hard_num.set_alpha(255)
                    self.button_master.set_alpha(255)
                    self.master_diff.set_alpha(255)
                    self.master_num.set_alpha(255)
                case (
                    x,
                    y,
                ) if self.button_normal_rect.left < x < self.button_normal_rect.right and self.button_normal_rect.top < y < self.button_normal_rect.bottom:
                    self.button_normal.set_alpha(100)
                    self.normal_diff.set_alpha(100)
                    self.normal_num.set_alpha(100)
                    self.hover_normal = True
                    self.hover_easy = False
                    self.hover_hard = False
                    self.hover_master = False
                    self.button_easy.set_alpha(255)
                    self.easy_diff.set_alpha(255)
                    self.easy_num.set_alpha(255)
                    self.button_hard.set_alpha(255)
                    self.hard_diff.set_alpha(255)
                    self.hard_num.set_alpha(255)
                    self.button_master.set_alpha(255)
                    self.master_diff.set_alpha(255)
                    self.master_num.set_alpha(255)
                case (
                    x,
                    y,
                ) if self.button_hard_rect.left < x < self.button_hard_rect.right and self.button_hard_rect.top < y < self.button_hard_rect.bottom:
                    self.button_hard.set_alpha(100)
                    self.hard_diff.set_alpha(100)
                    self.hard_num.set_alpha(100)
                    self.hover_hard = True
                    self.hover_easy = False
                    self.hover_normal = False
                    self.hover_master = False
                    self.button_easy.set_alpha(255)
                    self.easy_diff.set_alpha(255)
                    self.easy_num.set_alpha(255)
                    self.button_normal.set_alpha(255)
                    self.normal_diff.set_alpha(255)
                    self.normal_num.set_alpha(255)
                    self.button_master.set_alpha(255)
                    self.master_diff.set_alpha(255)
                    self.master_num.set_alpha(255)
                case (
                    x,
                    y,
                ) if self.button_master_rect.left < x < self.button_master_rect.right and self.button_master_rect.top < y < self.button_master_rect.bottom:
                    self.button_master.set_alpha(100)
                    self.master_diff.set_alpha(100)
                    self.master_num.set_alpha(100)
                    self.hover_master = True
                    self.hover_easy = False
                    self.hover_normal = False
                    self.hover_hard = False
                    self.button_easy.set_alpha(255)
                    self.easy_diff.set_alpha(255)
                    self.easy_num.set_alpha(255)
                    self.button_normal.set_alpha(255)
                    self.normal_diff.set_alpha(255)
                    self.normal_num.set_alpha(255)
                    self.button_hard.set_alpha(255)
                    self.hard_diff.set_alpha(255)
                    self.hard_num.set_alpha(255)
                case _:
                    self.lite_img = self.load_lite_img()
                    self.rmap_button.set_alpha(255)
                    self.lmap_button.set_alpha(255)
                    self.back_button.set_alpha(255)
                    self.info_button.set_alpha(255)
                    self.button_easy.set_alpha(255)
                    self.easy_diff.set_alpha(255)
                    self.easy_num.set_alpha(255)
                    self.button_normal.set_alpha(255)
                    self.normal_diff.set_alpha(255)
                    self.normal_num.set_alpha(255)
                    self.button_hard.set_alpha(255)
                    self.hard_diff.set_alpha(255)
                    self.hard_num.set_alpha(255)
                    self.button_master.set_alpha(255)
                    self.master_diff.set_alpha(255)
                    self.master_num.set_alpha(255)
                    self.hover_right = False
                    self.hover_left = False
                    self.hover_back = False
                    self.hover_info = False
                    self.hover_easy = False
                    self.hover_normal = False
                    self.hover_hard = False
                    self.hover_master = False
                    self.hover_play = False

    def draw(self) -> None:
        # TODO: Refactor this wall of bad code
        self.ctx.Display.blit(self.bg, (0, 0))
        self.ctx.Display.blit(self.overlay, (0, 0))
        self.ctx.Display.blit(self.rmap_button, self.rmap_button_rect)
        self.ctx.Display.blit(self.lmap_button, self.lmap_button_rect)
        self.ctx.Display.blit(self.info_button, self.info_button_rect)
        self.ctx.Display.blit(self.song_text, self.song_text_rect)
        self.ctx.Display.blit(self.back_button, self.back_button_rect)
        self.ctx.Display.blit(self.button_easy, self.button_easy_rect)
        self.ctx.Display.blit(self.easy_diff, self.easy_diff_rect)
        self.ctx.Display.blit(self.easy_num, self.easy_num_rect)
        self.ctx.Display.blit(self.button_normal, self.button_normal_rect)
        self.ctx.Display.blit(self.normal_diff, self.normal_diff_rect)
        self.ctx.Display.blit(self.normal_num, self.normal_num_rect)
        self.ctx.Display.blit(self.button_hard, self.button_hard_rect)
        self.ctx.Display.blit(self.hard_diff, self.hard_diff_rect)
        self.ctx.Display.blit(self.hard_num, self.hard_num_rect)
        self.ctx.Display.blit(self.button_master, self.button_master_rect)
        self.ctx.Display.blit(self.master_diff, self.master_diff_rect)
        self.ctx.Display.blit(self.master_num, self.master_num_rect)
        self.ctx.Display.blit(self.diamond_easy, self.diamond_easy_rect)
        self.ctx.Display.blit(self.grade_easy, self.grade_easy_rect)
        self.ctx.Display.blit(self.diamond_normal, self.diamond_normal_rect)
        self.ctx.Display.blit(self.grade_normal, self.grade_normal_rect)
        self.ctx.Display.blit(self.diamond_hard, self.diamond_hard_rect)
        self.ctx.Display.blit(self.grade_hard, self.grade_hard_rect)
        self.ctx.Display.blit(self.diamond_master, self.diamond_master_rect)
        self.ctx.Display.blit(self.grade_master, self.grade_master_rect)
        self.ctx.Display.blit(self.diff_arrow, self.diff_arrow_rect)

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
            self.ctx.Display.blit(self.info_vocals_text, self.info_vocals_text_rect)
            self.ctx.Display.blit(self.info_mapper_text, self.info_mapper_text_rect)
            self.ctx.Display.blit(self.info_avocals, self.info_avocals_rect)
            self.ctx.Display.blit(self.info_amapper, self.info_amapper_rect)
            self.ctx.Display.blit(self.info_disclaimer, self.info_disclaimer_rect)
