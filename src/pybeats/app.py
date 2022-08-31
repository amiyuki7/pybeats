from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from threading import Thread
from typing import Dict, List, Literal, Optional, Tuple, Type

import pygame as pg
from pygame import font, mixer

from pygame.surface import Surface

from .conf import Conf
from .lib import NoteData, SongData, fetch_song_data, panic, screen_res

pg.init()

mixer.pre_init(Conf.SOUND_BUFFER_SIZE)
mixer.set_reserved(1)
mixer.set_reserved(2)
mixer.set_num_channels(Conf.MIXER_CHANNELS)

font.init()

from pybeats import ROOT_DIR

pg.mouse.set_visible(False)


class MixerWrapper:
    def __init__(self) -> None:
        self.paused: bool = False
        self.playing: bool = False

    # def toggle_pause(self) -> None:
    #     if self.playing:
    #         if self.paused:
    #             mixer.music.unpause()
    #         else:
    #             mixer.music.pause()
    #             self.paused = True
    #     else:
    #         mixer.music.play()
    #         self.playing = True

    @staticmethod
    def load(song_file: str) -> None:
        mixer.music.load(song_file)

    @staticmethod
    def unload() -> None:
        mixer.music.unload()

    @staticmethod
    def play() -> None:
        mixer.music.play()

    @staticmethod
    def set_volume(volume: float) -> None:
        mixer.music.set_volume(volume)

    @staticmethod
    def get_volume() -> float:
        return mixer.music.get_volume()

    @staticmethod
    def get_music_pos() -> int:
        return mixer.music.get_pos()

    @staticmethod
    def play_sfx(sfx: mixer.Sound, channel: Optional[mixer.Channel] = None) -> None:
        if channel:
            channel.play(sfx)
        mixer.find_channel().play(sfx)


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
                self.ctx.mixer.play_sfx(self.ctx.sfx.tap_perfect)
            case "tc":
                self.ctx.mixer.play_sfx(self.ctx.sfx.tap_crit)
            case "f":
                self.ctx.mixer.play_sfx(self.ctx.sfx.flair)
            case "fc":
                self.ctx.mixer.play_sfx(self.ctx.sfx.flair_crit)
            case "h":
                self.ctx.mixer.play_sfx(self.ctx.sfx.tap_perfect, self.ctx.HoldHeadChannel)
                self.ctx.mixer.play_sfx(
                    mixer.Sound(f"{ROOT_DIR}/beatmaps/{self.song}/holdbeats/hold_{length}.wav"),
                    self.ctx.HoldChannel,
                )
            case "hr":
                self.ctx.mixer.play_sfx(self.ctx.sfx.tap_perfect)
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
        frame = pg.transform.scale(frame, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
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
        self.fade_overlay = Surface((self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT))
        self.fade_overlay.fill((0, 0, 0))

        self.has_toggled_mode: bool = False

        # Fading out music when going from State -> SongSelect
        self.adjust_volume_flag: bool = False

    def fadein(self) -> None:
        self.fade_alpha -= 5

        self.fade_overlay.set_alpha(self.fade_alpha)
        if self.fade_alpha <= 0:
            self.set_mode(None)
            self.adjust_volume_flag = False

    def fadeout(self) -> None:
        self.fade_alpha += 5

        if self.adjust_volume_flag:
            self.ctx.mixer.set_volume(self.ctx.mixer.get_volume() - 0.02)

        self.fade_overlay.set_alpha(self.fade_alpha)

    def fade_to_state(self, state: Type[State]) -> None:
        self.set_mode("out")

        if state == SongSelect:
            self.adjust_volume_flag = True

        if self.fade_alpha >= 255:
            self.set_mode(None)
            self.ctx.setState(state)
            self.set_mode("in")

    def render(self) -> None:
        self.ctx.Display.blit(self.fade_overlay, (0, 0))

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
            self.ctx.Display.blit(self.fade_overlay, (0, 0))
            return

        if self.has_toggled_mode:
            return

        self.mode = mode
        self.fade_alpha: int = mode == "in" and 255 or 0

        self.has_toggled_mode = True


from .states.loading import Loading
from .states.menu import Menu
from .states.songselect import SongSelect


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
        "assets/info_icon.jpg",
        "assets/button_easy.jpg",
        "assets/button_normal.jpg",
        "assets/button_hard.jpg",
        "assets/button_master.jpg",
        "assets/diamond_gray.jpg",
        "assets/diamond_green.jpg",
        "assets/diamond_pink.jpg",
        "assets/diamond_prismatic.jpg",
        "assets/back_icon.jpg",
        "assets/diff_arrow.jpg",
        "assets/info_pad.jpg",
        "beatmaps/ド屑/images/cover_avatar.jpg",
        "beatmaps/ド屑/images/lite.jpg",
        "beatmaps/ド屑/images/vocaloid_avatar.jpg",
        "beatmaps/ゴーストルール/images/cover_avatar.jpg",
        "beatmaps/ゴーストルール/images/lite.jpg",
        "beatmaps/ゴーストルール/images/vocaloid_avatar.jpg",
    ]

    maps: List[Video]

    def __init__(self, init_state: Type[State]) -> None:
        self.HoldChannel = mixer.Channel(1)
        self.HoldHeadChannel = mixer.Channel(2)

        self.SCREEN_WIDTH, self.SCREEN_HEIGHT = screen_res(pg.display.Info())

        self.Display = pg.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), Conf.FLAGS, 16)
        pg.display.set_caption("PyBeats")

        self.Clock = pg.time.Clock()

        self.mixer = MixerWrapper()

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
            play_title = mixer.Sound(f"{SFX_DIR}/play_title2.wav")
            play_game = mixer.Sound(f"{SFX_DIR}/play_game.wav")

            # Song select screen R/L buttons
            switch_button = mixer.Sound(f"{SFX_DIR}/switch_button2.wav")

            back = mixer.Sound(f"{SFX_DIR}/back.wav")

            info_in = mixer.Sound(f"{SFX_DIR}/info_in2.wav")
            info_out = mixer.Sound(f"{SFX_DIR}/info_out2.wav")

        self.sfx = Sfx

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
        self.setState(init_state)

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

        if pressed_keys[pg.K_SPACE]:
            pass

    def check_events(self) -> None:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                self.check_keys()
            if event.type == pg.MOUSEBUTTONDOWN:
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
                        self.mixer.play_sfx(self.sfx.switch_button)
                        self._state.switch_map()
                    elif self._state.hover_info:
                        self.mixer.play_sfx(self.sfx.info_in)
                        self._state.show_info()
                    elif self._state.hover_out:
                        self.mixer.play_sfx(self.sfx.info_out)
                        self._state.hide_info()
                    elif self._state.hover_back:
                        self.mixer.play_sfx(self.sfx.back)
                        self._state.back = True
                        self.mixer.unload()
                        self.mixer.load(f"{ROOT_DIR}/audio/君の夜をくれ3.mp3")
                        self.mixer.play()

    def manage_states(self) -> None:
        if type(self._state) is Loading and self._state.load_task(self.load_cache):
            self.fader.fade_to_state(Menu)

        if type(self._state) is Menu and self._state.title.get_alpha() == 0:
            self.fader.fade_to_state(SongSelect)

        if type(self._state) is SongSelect and self._state.back:
            self.fader.fade_to_state(Menu)

    def run(self) -> None:
        self.mixer.load(f"{ROOT_DIR}/audio/君の夜をくれ3.mp3")
        self.mixer.play()

        while 1:
            self.check_events()
            self.manage_states()
            self.update()
            self.draw()
            self.fader.update()

            self.cursor_rect = self.cursor.get_rect(center=pg.mouse.get_pos())
            self.Display.blit(self.cursor, self.cursor_rect)

            pg.display.update()
            self.Clock.tick(Conf.TARGET_FPS)
