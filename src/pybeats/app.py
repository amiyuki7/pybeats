from __future__ import annotations

import os
import sys
import time
from abc import ABC, abstractmethod
from math import floor
from threading import Thread
from typing import Callable, Dict, List, Literal, Optional, Tuple, Type

import pygame as pg
from pygame import font, mixer
from pygame.locals import *
from pygame.surface import Surface

from .conf import Colours, Conf
from .lib import NoteData, SongData, fetch_song_data, panic, screen_res

pg.init()

mixer.pre_init(Conf.SOUND_BUFFER_SIZE)
mixer.set_reserved(1)
mixer.set_reserved(2)
mixer.set_num_channels(Conf.MIXER_CHANNELS)

font.init()

ROOT_DIR = Conf.ROOT_DIR

SCREEN_WIDTH, SCREEN_HEIGHT = screen_res(pg.display.Info())

Display = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), Conf.FLAGS, 16)
pg.display.set_caption("PyBeats")

pg.mouse.set_visible(False)


class Sfx:
    SFX_DIR = f"{ROOT_DIR}/audio/sfx"
    # Tap null
    tap_lane = mixer.Sound(f"{SFX_DIR}/tap_lane.wav")
    tap_lane_trunc = mixer.Sound(f"{SFX_DIR}/tap_lane_trunc.wav")
    # Tap note
    tap_perfect = mixer.Sound(f"{SFX_DIR}/tap.wav")
    tap_crit = mixer.Sound(f"{SFX_DIR}/tap_crit.wav")
    # Tap note (Great/Good/Bad)
    tap_etc = mixer.Sound(f"{SFX_DIR}/tap_etc.wav")
    # Hold note
    hold = mixer.Sound(f"{SFX_DIR}/hold.wav")
    # Flair note
    flair = mixer.Sound(f"{SFX_DIR}/flair.wav")
    flair_crit = mixer.Sound(f"{SFX_DIR}/flair_crit.wav")
    # Major buttons
    play_title = mixer.Sound(f"{SFX_DIR}/play_title.wav")
    play_game = mixer.Sound(f"{SFX_DIR}/play_game.wav")

    # Song select screen R/L buttons
    switch_button = mixer.Sound(f"{SFX_DIR}/switch_button.wav")


class MixerWrapper:
    def __init__(self) -> None:
        self.paused: bool = False
        self.playing: bool = False

    def toggle_pause(self) -> None:
        if self.playing:
            if self.paused:
                mixer.music.unpause()
            else:
                mixer.music.pause()
                self.paused = True
        else:
            mixer.music.play()
            self.playing = True

    def load(self, song_file: str) -> None:
        mixer.music.load(song_file)

    def play_sfx(self, sfx: mixer.Sound, channel: Optional[mixer.Channel] = None) -> None:
        if channel:
            channel.play(sfx)
        mixer.find_channel().play(sfx)


# Mixer = MixerWrapper()


class Conductor:
    def __init__(self, ctx: App, bpm: int, song: str, note_data: NoteData) -> None:
        self.ctx = ctx

        self.song = song
        self.bpm = bpm
        self.sec_per_beat = 60 / bpm
        self.pos = mixer.music.get_pos()
        self.beat_count = 0

        self.played: bool = False

        self.note_data = note_data
        self.next_note = note_data.next_note_beat

    def update(self) -> None:
        self.pos = mixer.music.get_pos()

        if (note_list := self.note_data.notes.get(str(self.beat_count - 1))) and not self.played:
            # Debug
            print(list(map(lambda note: note.type, note_list)))

            for note in note_list:
                self.play_sound(note.type, note.length)

            self.played = True

        if self.pos >= (self.beat_count) * self.sec_per_beat * 1000:
            self.beat_count += 1
            self.played = False

    def play_sound(self, note_type: str, length: Optional[int]) -> None:
        match note_type:
            case "t":
                self.ctx.mixer.play_sfx(Sfx.tap_perfect)
            case "tc":
                self.ctx.mixer.play_sfx(Sfx.tap_crit)
            case "f":
                self.ctx.mixer.play_sfx(Sfx.flair)
            case "fc":
                self.ctx.mixer.play_sfx(Sfx.flair_crit)
            case "h":
                self.ctx.mixer.play_sfx(Sfx.tap_perfect, self.ctx.HoldHeadChannel)
                self.ctx.mixer.play_sfx(
                    mixer.Sound(f"{ROOT_DIR}/beatmaps/{self.song}/holdbeats/hold_{length}.wav"),
                    self.ctx.HoldChannel,
                )
            case "hr":
                self.ctx.mixer.play_sfx(Sfx.tap_perfect)
            case other:
                """
                This panic will only occur when there's a value in the `t` field of a note in a
                beatmap's `meta.toml` that doesn't correspond with: 't'|'tc'|'f'|'fc'|'h'|'hr'
                """
                raise Exception(panic(f"Bad beatmap config: Unknown note type, found {other}"))


class Video:
    def __init__(self, ctx: App, rpath: str, image_name: str) -> None:
        self.ctx = ctx
        self.frames_path = rpath
        self.image_name = image_name

        self.frames: Dict[int, Surface] = {}

        self.frame_count = len(os.listdir(self.frames_path))

        self.load_curr: int = 1

    def load_and_scale(self, path: str) -> Surface:
        frame = pg.image.load(path)
        frame = pg.transform.scale(frame, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
        frame.set_alpha(30)
        return frame

    def load_next(self, adder: int) -> None:
        # An adder is used so a Mutex is not necessary

        frame = self.load_and_scale(f"{self.frames_path}/{self.image_name}{self.load_curr + adder}.jpg")

        # Simulate List like indexing
        self.frames[self.load_curr + adder] = frame

    def load_chunk_buf(self) -> None:
        # Finished loading
        if self.load_curr > self.frame_count:
            return

        threads: List[Thread] = []

        # Use Conf.MAX_ALLOWED_THREADS, but if the number of images left to be loaded is less than Conf.MAX_ALLOWED_THREADS use that.
        max_threads = (
            (self.frame_count - self.load_curr > Conf.MAX_ALLOWED_THREADS)
            and Conf.MAX_ALLOWED_THREADS
            or self.frame_count - self.load_curr + 1
        )

        for i in range(0, max_threads):
            thread = Thread(target=self.load_next, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.load_curr += Conf.MAX_ALLOWED_THREADS

    def unload(self) -> None:
        """
        Frees the memory being consumed by Video.frames

        *Call gc.collect() immediately after calling this method
        """
        self.frames = {}
        self.load_curr = 1


class State(ABC):
    _ctx: App

    def __init__(self, ctx: App) -> None:
        self.ctx = ctx

    @property
    def ctx(self) -> App:
        return self._ctx

    @ctx.setter
    def ctx(self, ctx: App) -> None:
        self._ctx = ctx

    @abstractmethod
    def update(self) -> None:
        """
        Update any background variables and the properties of visual objects on the display

        *Should only be called by the App class
        """
        ...

    @abstractmethod
    def draw(self) -> None:
        """
        Render visual objects onto the display with respect to the State

        *Should only be called by the App class
        """
        ...


class Loading(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg = Colours.Black

        self.progress = 0

        self.loading_bar_rect = pg.Rect(0, 0, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 8)
        self.loading_bar_rect.center = Display.get_rect().center

        self.progress_rect = pg.Rect(0, 0, 0, self.loading_bar_rect.height - 10)
        self.progress_rect.x = self.loading_bar_rect.x + 5
        self.progress_rect.centery = self.loading_bar_rect.centery

        font_size = SCREEN_HEIGHT // 18
        self.font = font.SysFont("Monospace", font_size)
        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

    def update(self) -> None:
        self.progress_rect.width = floor(self.loading_bar_rect.width * self.progress / 100) - 10

        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

    def draw(self) -> None:
        Display.fill(self.bg)
        pg.draw.rect(Display, (121, 183, 172), self.loading_bar_rect, 5)
        pg.draw.rect(Display, (161, 223, 212), self.progress_rect)

        # Scale is used for responsive UI
        text_pos_scale = 14
        Display.blit(
            self.progress_surface,
            (
                self.progress_rect.right - self.progress_surface.get_width() / 2,
                self.progress_rect.top - SCREEN_HEIGHT / text_pos_scale,
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


class Menu(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg: Surface = self.ctx.image_cache["assets/menu_tint.jpg"]
        self.bg = pg.transform.scale(self.bg, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay.set_alpha(128)
        self.overlay.fill(Colours.Black)

        self.title: Surface = pg.image.load(f"{ROOT_DIR}/assets/Pybeats_text.jpg")

        scale = SCREEN_WIDTH * 0.8 / self.title.get_width()

        self.title = pg.transform.scale(
            self.title, (self.title.get_width() * scale, self.title.get_height() * scale)
        ).convert_alpha()

        self.title_rect = self.title.get_rect(center=Display.get_rect().center)
        self.title_rect.y = SCREEN_HEIGHT // 6

        font_scale = 10
        self.font = font.Font(f"{ROOT_DIR}/Mylodon-Light.otf", SCREEN_HEIGHT // font_scale)

        self.play_text = self.font.render("    Play    ", True, (120, 120, 120))
        self.play_rect = self.play_text.get_rect(center=Display.get_rect().center)
        self.play_rect.y = SCREEN_HEIGHT // 6 * 3

        self.options_text = self.font.render("  Options  ", True, (120, 120, 120))
        self.options_rect = self.options_text.get_rect(center=Display.get_rect().center)
        self.options_rect.y = SCREEN_HEIGHT // 6 * 4

        self.hover_play = False
        self.hover_options = False

        self.prev_hovering = False
        self.hovering = False

        self.switchf = False
        self.shift_dist = SCREEN_HEIGHT // 500
        self.fade_speed = 8

    def update(self) -> None:
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

            self.play_rect = self.play_text.get_rect(center=Display.get_rect().center)
            self.play_rect.y = SCREEN_HEIGHT // 6 * 3
            self.options_rect = self.options_text.get_rect(center=Display.get_rect().center)
            self.options_rect.y = SCREEN_HEIGHT // 6 * 4

            temp = self.hovering
            self.hovering = self.hover_play or self.hover_options
            self.prev_hovering = temp

            if not self.prev_hovering and self.prev_hovering != self.hovering:
                self.ctx.mixer.play_sfx(Sfx.tap_lane_trunc)

    def switch(self) -> None:
        self.switchf = True
        self.hover_play = False
        self.ctx.mixer.play_sfx(Sfx.play_title)

    def draw(self) -> None:
        Display.blit(self.bg, (0, 0))
        Display.blit(self.overlay, (0, 0))
        Display.blit(self.title, self.title_rect)
        Display.blit(self.play_text, self.play_rect)
        Display.blit(self.options_text, self.options_rect)


class SongSelect(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        # 0 => ド屑
        # 1 => ゴーストルール
        # などなど
        self.song_idx = 0
        self.song_ref = self.ctx.song_cache[self.ctx.song_names[self.song_idx]]

        self.bg: Surface = self.ctx.image_cache["assets/menu_tint.jpg"]
        self.bg = pg.transform.scale(self.bg, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay.set_alpha(128)
        self.overlay.fill(Colours.Black)

        self.target_song: int = 1

        self.frame: Surface = self.ctx.image_cache["assets/frame90.jpg"]

        scale = SCREEN_WIDTH * 0.6 / self.frame.get_width()
        self.frame = pg.transform.scale(
            self.frame, (self.frame.get_width() * scale, self.frame.get_height() * scale)
        ).convert_alpha()
        self.frame_rect = self.frame.get_rect(center=Display.get_rect().center)
        self.frame_rect.y = SCREEN_HEIGHT // 7

        self.frame.set_alpha(255)

        self.lite_img = self.load_lite_img()
        self.prev_img: Optional[Surface] = None

        self.rmap_button = self.ctx.image_cache["assets/switch_button_1_crop.jpg"]
        scale = SCREEN_WIDTH * 0.05 / self.rmap_button.get_width()

        # Blue on top, purple on bottom
        self.rmap_button = pg.transform.flip(
            pg.transform.scale(
                self.rmap_button, (self.rmap_button.get_width() * scale, self.rmap_button.get_height() * scale)
            ),
            flip_x=False,
            flip_y=True,
        ).convert_alpha()
        self.rmap_button_rect = self.rmap_button.get_rect()
        self.rmap_button_rect.x = SCREEN_WIDTH // 10 * 9 - self.rmap_button_rect.width
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
        self.lmap_button_rect.x = SCREEN_WIDTH // 10
        self.lmap_button_rect.centery = self.frame_rect.centery

        self.hover_right = False
        self.hover_left = False

        self.switching = False
        self.switching_left = False

        self.prev_percent: int = 0

    def load_lite_img(self) -> Surface:
        scale = SCREEN_WIDTH * 0.6 / self.ctx.image_cache["assets/frame90.jpg"].get_width()
        img = self.ctx.image_cache[self.song_ref.lite_img]

        img = pg.transform.scale(img, (img.get_width() * scale, img.get_height() * scale)).convert_alpha()

        img.set_alpha(250)
        return img

    def switch_map(self) -> None:
        self.switching = True

        # When the index reaches either end of the list, go to the other end
        if self.hover_right:
            self.song_idx += 1
            if self.song_idx >= len(self.ctx.song_names):
                self.song_idx = 0

        elif self.hover_left:
            self.song_idx -= 1
            if self.song_idx < 0:
                self.song_idx = len(self.ctx.song_names) - 1
            self.switching_left = True

        self.hover_right = False
        self.hover_left = False

        self.prev_img = self.lite_img
        self.song_ref = self.ctx.song_cache[self.ctx.song_names[self.song_idx]]
        self.lite_img = self.load_lite_img()

        self.prev_percent = 100

    def update(self) -> None:
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

            print(self.prev_percent)

        else:
            match cursor:
                # Detecting the opacity of the Surface; the Surface is a rectangle but only part of that rectangle is the actual button
                case (
                    x,
                    y,
                ) if self.rmap_button_rect.left < x < self.rmap_button_rect.right and self.rmap_button_rect.top < y < self.rmap_button_rect.bottom and (
                    px_alpha := self.rmap_button.get_at([x - self.rmap_button_rect.x, y - self.rmap_button_rect.y])[3]
                ):
                    if px_alpha > 0:
                        self.rmap_button.set_alpha(100)
                        self.hover_right = True
                case (
                    x,
                    y,
                ) if self.lmap_button_rect.left < x < self.lmap_button_rect.right and self.lmap_button_rect.top < y < self.lmap_button_rect.bottom and (
                    px_alpha := self.lmap_button.get_at([x - self.lmap_button_rect.x, y - self.lmap_button_rect.y])[3]
                ):
                    if px_alpha > 0:
                        self.lmap_button.set_alpha(100)
                        self.hover_left = True
                case _:
                    self.rmap_button.set_alpha(255)
                    self.lmap_button.set_alpha(255)
                    self.hover_right = False
                    self.hover_left = False

    def draw(self) -> None:
        Display.blit(self.bg, (0, 0))
        Display.blit(self.overlay, (0, 0))
        Display.blit(self.rmap_button, self.rmap_button_rect)
        Display.blit(self.lmap_button, self.lmap_button_rect)

        if self.prev_img:
            # Gradually draw the next song's lite_img over the old one
            part_img = Surface.copy(self.lite_img)
            pixels_removed_b = part_img.get_width() * self.prev_percent / 100

            for w in range(floor(pixels_removed_b)):
                for h in range(part_img.get_height()):
                    part_img.set_at((self.switching_left and part_img.get_width() - w or w, h), (255, 255, 255, 0))

            Display.blit(self.prev_img, self.frame_rect)
            Display.blit(part_img, self.frame_rect)

            Display.blit(self.frame, self.frame_rect)
        else:
            # Normal
            Display.blit(self.lite_img, (self.frame_rect.x, self.frame_rect.y))
            Display.blit(self.frame, self.frame_rect)


class InGame(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

    def update(self) -> None:
        return super().update()

    def draw(self) -> None:
        return super().draw()


class FadeOverlay:
    """
    This is probably 'overcoded' but it works...
    """

    def __init__(self, ctx: App, mode: Optional[Literal["in", "out"]]) -> None:
        self.ctx = ctx
        self.mode = mode
        self.fade_alpha: int = mode == "in" and 255 or 0
        self.fade_overlay = Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.fade_overlay.fill(Colours.Black)

        self.has_toggled_mode: bool = False

    def fadein(self) -> None:
        self.fade_alpha -= 5
        self.fade_overlay.set_alpha(self.fade_alpha)
        if self.fade_alpha <= 0:
            self.set_mode(None)

    def fadeout(self) -> None:
        self.fade_alpha += 5
        self.fade_overlay.set_alpha(self.fade_alpha)

    def fade_to_state(self, state: Type[State]) -> None:
        self.set_mode("out")
        if self.fade_alpha >= 255:
            self.set_mode(None)
            self.ctx.setState(state)
            self.set_mode("in")

    def render(self) -> None:
        Display.blit(self.fade_overlay, (0, 0))

    def update(self) -> None:
        if self.mode == None:
            return

        if self.mode == "in":
            self.fadein()
            self.render()
        elif self.mode == "out":
            self.fadeout()
            self.render()

    def set_mode(self, mode: Optional[Literal["in", "out"]]) -> None:
        if mode is None:
            self.mode = None
            self.has_toggled_mode = False
            self.fade_alpha = 0
            self.fade_overlay.set_alpha(self.fade_alpha)
            Display.blit(self.fade_overlay, (0, 0))
            return

        if self.has_toggled_mode:
            return

        self.mode = mode
        self.fade_alpha: int = mode == "in" and 255 or 0

        self.has_toggled_mode = True


class App:
    _state: State

    song_cache: Dict[str, SongData] = {}
    image_cache: Dict[str, Surface] = {}

    song_names = ["ド屑", "ゴーストルール"]

    image_paths = [
        "assets/menu_tint.jpg",
        "assets/Pybeats_text.jpg",
        "assets/ingame.jpg",
        "assets/frame90.jpg",
        "assets/switch_button_1_crop.jpg",
        "beatmaps/ド屑/images/cover_avatar.jpg",
        "beatmaps/ド屑/images/lite.jpg",
        "beatmaps/ド屑/images/vocaloid_avatar.jpg",
        "beatmaps/ゴーストルール/images/lite.jpg",
        "beatmaps/ゴーストルール/images/vocaloid_avatar.jpg",
    ]

    maps: List[Video]

    def __init__(self, init_state: Type[State]) -> None:
        self.HoldChannel = mixer.Channel(1)
        self.HoldHeadChannel = mixer.Channel(2)

        self.Clock = pg.time.Clock()

        self.setState(init_state)
        self.mixer: MixerWrapper = MixerWrapper()

        self.fader = FadeOverlay(ctx=self, mode=None)

        self.maps = [
            Video(ctx=self, rpath=f"{ROOT_DIR}/beatmaps/ド屑/frames/", image_name="dokuzu"),
        ]

        self.cursor = pg.image.load(f"{ROOT_DIR}/assets/cursor.jpg").convert_alpha()
        cursor_scale = self.cursor.get_width() / 40
        self.cursor = pg.transform.scale(
            self.cursor, (self.cursor.get_width() / cursor_scale, self.cursor.get_height() / cursor_scale)
        )
        self.cursor.set_alpha(200)

    def setState(self, state: Type[State]) -> None:
        self._state = state(self)

    def update(self) -> None:
        self._state.update()

    def draw(self) -> None:
        self._state.draw()

    def load_cache(self) -> Tuple[int, int]:
        """
        Sequentially caches song data and essential images on a single thread

        *Should only be passed as an argument to Loading.load_task()
        """

        # Cache song data first, then cache image data
        if (next_item := len(self.song_cache)) < len(self.song_names):
            next_song = self.song_names[next_item]
            self.song_cache[next_song] = fetch_song_data(next_song)

        elif (next_item := len(self.image_cache)) < len(self.image_paths):
            next_image = self.image_paths[next_item]

            img = pg.image.load(f"{ROOT_DIR}/{next_image}").convert()

            self.image_cache[next_image] = img

        curr_progress = len(self.song_cache) + len(self.image_cache)
        total_progress = len(self.song_names) + len(self.image_paths)

        return (curr_progress, total_progress)

    def check_keys(self) -> None:
        pressed_keys = pg.key.get_pressed()

        if pressed_keys[K_SPACE]:
            pass

    def check_events(self) -> None:
        for event in pg.event.get():
            if event.type == QUIT:
                pg.quit()
                sys.exit()
            if event.type == KEYDOWN:
                self.check_keys()
            if event.type == MOUSEBUTTONDOWN:
                if type(self._state) is Menu:
                    if self._state.hover_options:
                        # Debug
                        print("Options coming soon!")
                    if self._state.hover_play:
                        # Debug
                        print("PLAY")
                        self._state.switch()

                if type(self._state) is SongSelect:
                    if self._state.hover_right or self._state.hover_left:
                        self.mixer.play_sfx(Sfx.switch_button)
                        self._state.switch_map()

    def manage_states(self) -> None:
        if type(self._state) is Loading and self._state.load_task(self.load_cache):
            self.fader.fade_to_state(Menu)

        if type(self._state) is Menu and self._state.title.get_alpha() == 0:
            self.fader.fade_to_state(SongSelect)

    def run(self) -> None:
        while 1:
            self.check_events()
            self.manage_states()
            self.update()
            self.draw()
            self.fader.update()

            self.cursor_rect = self.cursor.get_rect(center=pg.mouse.get_pos())
            Display.blit(self.cursor, self.cursor_rect)

            pg.display.update()
            self.Clock.tick(Conf.TARGET_FPS)
