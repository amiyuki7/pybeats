from __future__ import annotations

import time, os, sys
import pygame as pg
from math import floor
from time import sleep
import gc

import threading
from threading import Thread

from pygame import image, mixer, font
from pygame.surface import Surface
from pygame.font import Font
from pygame.locals import *

from typing import Callable, List, Optional, Tuple, Dict, Literal
from abc import ABC, abstractmethod

from conf import Conf, Colours
from lib import Note, NoteData, panic, screen_res, SongData, fetch_song_data

pg.init()

mixer.pre_init(Conf.SOUND_BUFFER_SIZE)

# Hold notes
mixer.set_reserved(1)
# Head of hold notes
mixer.set_reserved(2)

HoldChannel = mixer.Channel(1)
HoldHeadChannel = mixer.Channel(2)

mixer.set_num_channels(Conf.MIXER_CHANNELS)

font.init()

Clock = pg.time.Clock()

SCREEN_WIDTH, SCREEN_HEIGHT = screen_res(pg.display.Info())
Display = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), Conf.FLAGS, 16)

SONG_DATA = fetch_song_data("ド屑")
SONG_PATH = SONG_DATA.song_path
SONG_NAME = SONG_DATA.name
SONG_BPM = SONG_DATA.bpm_semiquaver


class Sfx:
    # Tapping the empty lane
    tap_lane = mixer.Sound("audio/sfx/tap_lane.wav")
    # Tap note
    tap_perfect = mixer.Sound("audio/sfx/tap.wav")
    tap_crit = mixer.Sound("audio/sfx/tap_crit.wav")
    # Tap note (Great/Good/Bad)
    tap_etc = mixer.Sound("audio/sfx/tap_etc.wav")
    # Hold note
    hold = mixer.Sound("audio/sfx/hold.wav")
    # Flair note
    flair = mixer.Sound("audio/sfx/flair.wav")
    flair_crit = mixer.Sound("audio/sfx/flair_crit.wav")


class MixerWrapper:
    def __init__(self) -> None:
        self.paused: bool = False
        self.playing: bool = False

        # mixer.music.load(SONG_PATH)

    def toggle_pause(self) -> None:
        if self.playing:
            if self.paused:
                mixer.music.unpause()
                self.paused = False
            else:
                mixer.music.pause()
                self.paused = True
        else:
            mixer.music.play()
            self.playing = True

    def load(self, song_file: str) -> None:
        mixer.music.load(song_file)


class Conductor:
    def __init__(self, bpm: int, song: str, note_data: NoteData) -> None:
        self.song = song
        self.bpm = bpm
        self.sec_per_beat = 60 / bpm
        self.pos = mixer.music.get_pos()
        self.beat_count = 0

        self.played: bool = False

        self.note_data = note_data
        self.next_note = note_data.next_note_beat

        ## TODO: Extend the hold note's sound effect to desired time; reserve a channel for that

    def update(self) -> None:
        self.pos = mixer.music.get_pos()

        if (note_list := self.note_data.notes.get(str(self.beat_count - 1))) and not self.played:
            # Debugging simultaneous notes
            print(list(map(lambda note: note.type, note_list)))

            ## TODO: Change into note spawning code
            for note in note_list:
                self.play_sound(note.type, note.length)

            self.played = True

        if self.pos >= (self.beat_count) * self.sec_per_beat * 1000:
            self.beat_count += 1
            self.played = False

    def play_sound(self, note_type: str, length: Optional[int]) -> None:
        match note_type:
            case "t":
                mixer.find_channel().play(Sfx.tap_perfect)
            case "tc":
                mixer.find_channel().play(Sfx.tap_crit)
            case "f":
                mixer.find_channel().play(Sfx.flair)
            case "fc":
                mixer.find_channel().play(Sfx.flair_crit)
            case "h":
                HoldHeadChannel.play(Sfx.tap_perfect)
                HoldChannel.play(mixer.Sound(f"beatmaps/{self.song}/holdbeats/hold_{length}.wav"))
            case "hr":
                mixer.find_channel().play(Sfx.tap_perfect)
            # うわあぁ〜 Python パターンをサポート！
            case other:
                """
                This panic will only occur when there's a value in the `t` field of a note in a
                beatmap's `meta.toml` that doesn't correspond with: 't'|'tc'|'f'|'fc'|'h'|'hr'
                """
                raise Exception(panic(f"Bad beatmap config: Unknown note type, found {other}"))


Song = Conductor(bpm=SONG_BPM, song=SONG_NAME, note_data=SONG_DATA.note_data)


class Video:
    def __init__(self, rpath: str, image_name: str) -> None:
        self.frames_path = os.path.join(os.getcwd(), rpath)
        self.image_name = image_name
        # Can't use a List[Surface] anymore because threads aren't executed in order
        # self.frames: List[Surface] = []

        self.frames: Dict[int, Surface] = {}

        self.frame_count = len(os.listdir(self.frames_path)) - 1

        # self.curr: int = 1
        # self.curr_frame: Surface = self.frames[self.curr]

        self.load_curr: int = 1

    def load_and_scale(self, path: str) -> Surface:
        frame = pg.image.load(path)
        frame = pg.transform.scale(frame, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
        frame.set_alpha(30)
        # transparency = 30 frame.fill((255, 255, 255, transparency), special_flags=pygame.BLEND_RGBA_MULT)
        return frame

    def load_next(self, adder: int) -> None:
        # Adder is used so that each thread doesn't need to modify load_curr using a Mutex

        # Load the next frame
        frame = self.load_and_scale(
            f"{self.frames_path}/{self.image_name}{self.load_curr + adder}.jpg"
        )
        # Add it to the frames dict
        self.frames[self.load_curr + adder] = frame

    def load_chunk_buffer(self) -> None:
        if self.load_curr > self.frame_count:
            return

        threads: List[Thread] = []

        max_threads = (
            (self.frame_count - self.load_curr > Conf.MAX_ALLOWED_THREADS)
            and Conf.MAX_ALLOWED_THREADS
            or self.frame_count - self.load_curr + 1
        )

        # Maximum of MAX_ALLOWED_THREADS threads at a time
        for n in range(0, max_threads):
            thread = Thread(target=self.load_next, args=(n,))
            threads.append(thread)
            thread.start()

        # Debugging
        # print(threading.active_count())

        for thread in threads:
            thread.join()

        self.load_curr += Conf.MAX_ALLOWED_THREADS


class GameObject(ABC):
    @abstractmethod
    def update(self) -> None:
        ...

    @abstractmethod
    def draw(self) -> None:
        ...


class Game:
    _state: State

    def __init__(self, init_state: State) -> None:
        self.setState(init_state)
        self.objects: List[GameObject] = []
        self.mixer: MixerWrapper = MixerWrapper()

    def setState(self, state: State) -> None:
        self._state = state
        # Give the new state object a reference to the Game class
        self._state.ctx = self

    def update(self) -> None:
        self._state.update()

    def draw(self) -> None:
        self._state.draw()


class State(ABC):
    # Protected Game context object
    _ctx: Game
    nodes: List[GameObject]

    @property
    def ctx(self) -> Game:
        return self._ctx

    @ctx.setter
    def ctx(self, ctx: Game) -> None:
        self._ctx = ctx

    @abstractmethod
    def update(self) -> None:
        ...

    @abstractmethod
    def draw(self) -> None:
        ...

    # @abstractmethod
    # def fadeout(self) -> None:
    #     ...


class Loading(State):
    def __init__(self) -> None:
        # Change to an image eventually
        self.bg = Colours.Black

        self.progress = 0

        self.loading_bar_rect = pg.Rect(0, 0, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 8)
        self.loading_bar_rect.center = Display.get_rect().center

        self.progress_rect = pg.Rect(0, 0, 0, self.loading_bar_rect.height - 10)
        self.progress_rect.x = self.loading_bar_rect.x + 5
        self.progress_rect.centery = self.loading_bar_rect.centery

        self.font = font.SysFont("Monospace", 30)
        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

        # self.fadeout_flag = False
        #
        # self.fade_overlay = Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        # self.fade_overlay.fill(Colours.Black)
        # self.fade_alpha = 0

    def update(self) -> None:
        # if self.fadeout_flag:
        #     self.fade_alpha += 5
        #     self.fade_overlay.set_alpha(self.fade_alpha)
        #     if self.fade_alpha >= 255:
        #         self.fadeout_flag = False
        #         # self.ctx.setState(Menu())

        self.progress_rect.width = floor(self.loading_bar_rect.width * self.progress / 100) - 10

        self.progress_text = f"{floor(self.progress)}%"
        self.progress_surface = self.font.render(self.progress_text, True, (255, 255, 255))

    def draw(self) -> None:
        Display.fill(self.bg)
        pg.draw.rect(Display, (121, 183, 172), self.loading_bar_rect, 5)
        pg.draw.rect(Display, (161, 223, 212), self.progress_rect)

        Display.blit(
            self.progress_surface,
            (
                self.progress_rect.right - self.progress_surface.get_width() / 2,
                self.progress_rect.top - 50,
            ),
        )

        # if self.fadeout_flag:
        #     Display.blit(self.fade_overlay, (0, 0))

    def load_task(self, func: Callable[..., Tuple[int, int]]) -> bool:
        done, total = func()

        self.progress = floor(done / total * 100)

        # if self.fade_alpha == 255:
        #     # Task is done
        #     return True

        # Task needs to continue loading
        return done == total

    # def fadeout(self) -> None:
    #     self.fadeout_flag = True
    #     # self.fade_alpha = 0


class Menu(State):
    def __init__(self) -> None:
        self.bg: Surface = pg.image.load("assets/menu.jpg")
        self.bg = pg.transform.scale(self.bg, (SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(200)

        self.overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.overlay.set_alpha(128)
        self.overlay.fill(Colours.Black)

    def update(self) -> None:
        pass

    def draw(self) -> None:
        Display.blit(self.bg, (0, 0))
        Display.blit(self.overlay, (0, 0))


class SongSelect(State):
    def update(self) -> None:
        return super().update()

    def draw(self) -> None:
        return super().draw()


class InGame(State):
    def update(self) -> None:
        return super().update()

    def draw(self) -> None:
        return super().draw()


# print("Initializing mixer...")
#
# Mixer = MixerWrapper()
# Mixer.load(SONG_PATH)
#
# print("Finished initializing mixer")


# MIXER_TOGGLE = pg.USEREVENT + 1


def check_keys() -> None:
    pressed_keys = pg.key.get_pressed()

    if pressed_keys[K_SPACE]:
        #     pg.event.post(pg.event.Event(MIXER_TOGGLE))
        pass


class FadeOverlay:
    """
    This is the code I wrote when I was frustrated; the quality is awful and I don't know what's really going on...
    But hey, it works〜
    """

    def __init__(self, mode: Optional[Literal["in", "out"]]) -> None:
        self.mode = mode
        self.fade_alpha: int = mode == "in" and 255 or 0
        self.fade_overlay = Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.fade_overlay.fill(Colours.Black)

        self.has_toggled_mode: bool = False

    def fadein(self) -> None:
        self.fade_alpha -= 5
        self.fade_overlay.set_alpha(self.fade_alpha)

    def fadeout(self) -> None:
        self.fade_alpha += 5
        self.fade_overlay.set_alpha(self.fade_alpha)
        print("Fading out... Alpha =", self.fade_alpha)

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


App = Game(Loading())
Map1 = Video(rpath="beatmaps/ド屑/frames/", image_name="dokuzu")

# Proof of concept
memory_not_freed = True

Fader = FadeOverlay(None)


def load_songs() -> Tuple[int, int]:
    Map1.load_chunk_buffer()

    if len(Map1.frames) == Map1.frame_count:
        print("DONE LOADING")
        # App._state.fadeout()

    ## NOTE: This might be redundant lmao
    return (len(Map1.frames), Map1.frame_count)


# START_TIME = time.perf_counter()

while True:
    for event in pg.event.get():
        if event.type == QUIT:
            pg.quit()
            sys.exit()
        # if event.type == MIXER_TOGGLE:
        #     Mixer.toggle_pause()
        if event.type == KEYDOWN:
            check_keys()

    # Song.update()

    if type(App._state) is Loading and not (App._state.load_task(load_songs)):
        # Debugging
        print(time.time())
    elif type(App._state) is Loading and (App._state.load_task(load_songs)):
        Fader.set_mode("out")
        if Fader.fade_alpha >= 255:
            Fader.set_mode(None)
            App.setState(Menu())
            print("Switched to menu")

    # Proof of concept
    # 明かした こんしけぷと… すごい！
    if type(App._state) is Menu and memory_not_freed:
        # END_TIME = time.perf_counter()
        # sleep(3)

        del Map1  # type: ignore
        gc.collect()
        print("FREED MEMORY")

        memory_not_freed = False
        # print(END_TIME - START_TIME)

    App.update()
    App.draw()
    Fader.update()

    pg.display.update()
    Clock.tick(Conf.TARGET_FPS)
