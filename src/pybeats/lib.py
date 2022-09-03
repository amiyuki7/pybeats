from __future__ import annotations

import colorama

from .conf import Conf
import toml
from typing import Any, Dict, List, Type, Literal
from collections import OrderedDict
from enum import Enum, auto


class Difficulty(Enum):
    Easy = auto()
    Normal = auto()
    Hard = auto()
    Master = auto()


def panic(content: str) -> str:
    RED = colorama.Fore.RED
    MAG = colorama.Fore.MAGENTA
    RES = colorama.Fore.RESET
    BRI = colorama.Style.BRIGHT

    return f"{BRI}{RED}[ERR]:{RES} {MAG}{content}{RES}"


def screen_res(meta) -> tuple[int, int]:
    h, w = meta.current_h, meta.current_w
    target_res = None

    # Proof of concept; comment the below line if you want your RAM stolen. Trust me, keep the res small as it is.
    h, w = 541, 961

    for res in Conf.SUPPORTED_RESOLUTIONS:
        if w > res["width"] and h > res["height"]:
            target_res = (res["width"], res["height"])
        if w <= res["width"] and h <= res["height"]:
            break

    try:
        assert target_res
    except AssertionError:
        raise AssertionError(panic("Screen size is too small! Minimum supported resolution is 1280 x 720"))

    return target_res


class Note:
    __slots__ = ("lane", "width", "type", "length")

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.lane: int = raw["l"]
        self.width: int = raw["w"]
        self.type: str = raw["t"]

        self.length: int = raw.get("ln") or 1

    @property
    def __dict__(self) -> Dict[str, Any]:
        return {s: getattr(self, s) for s in self.__slots__ if hasattr(self, s)}


class NoteData:
    def __init__(self, notes) -> None:
        self.notes: Dict[str, List[Note]] = OrderedDict(notes)
        self.__notes_iter = iter(self.notes)

    @property
    def next_note_beat(self) -> str:
        return next(self.__notes_iter)


class SongData:
    def __init__(self, o: Dict[str, Any]) -> None:
        self.name: str = o["name"]
        self.name_en: str = o["name_en"]
        self.image_name: str = o["image_name"]
        self.prod: str = o["prod"]
        self.prod_en: str = o["prod_en"]
        self.song_path: str = o["song_path"]
        self.lite_song_path: str = o["lite_song_path"]
        self.lite_img: str = o["lite_img"]
        self.questionable: bool = o["questionable"]
        self.bpm_crotchet: int = o["bpm_crotchet"]
        self.bpm_semiquaver: int = o["bpm_semiquaver"]
        self.bpm_semihemiquaver: int = o["bpm_semihemiquaver"]

        class Vocals:
            __o = o["vocals"]
            vocaloid: str = __o["vocaloid"]
            vocaloid_avatar: str = __o["vocaloid_avatar"]
            cover: str = __o["cover"]
            cover_avatar: str = __o["cover_avatar"]

        self.vocals = Vocals

        class Mv:
            __o = o["mv"]
            available: bool = __o["available"]
            frames_path: str = __o["frames_path"]

        self.mv = Mv

        class Difficulty:
            __o = o["difficulty"]
            easy: int = __o["easy"]
            normal: int = __o["normal"]
            hard: int = __o["hard"]
            # expert: int = __o["expert"]
            master: int = __o["master"]

        self.difficulty = Difficulty

        class Diamond:
            __o = o["diamond"]
            easy: Literal["AP", "FC", "CL", "NA"] = __o["easy"]
            normal: Literal["AP", "FC", "CL", "NA"] = __o["normal"]
            hard: Literal["AP", "FC", "CL", "NA"] = __o["hard"]
            master: Literal["AP", "FC", "CL", "NA"] = __o["master"]

        self.diamond = Diamond

        class Grade:
            __o = o["grade"]
            easy: Literal["C", "B", "A", "S"] = __o["easy"]
            normal: Literal["C", "B", "A", "S"] = __o["normal"]
            hard: Literal["C", "B", "A", "S"] = __o["hard"]
            master: Literal["C", "B", "A", "S"] = __o["master"]

        self.grade = Grade

        easy = o["map_easy"]
        for k, v in easy.items():
            easy[k] = [Note(note) for note in v]

        self.map_easy: NoteData = NoteData(easy)

        normal = o["map_normal"]
        for k, v in normal.items():
            normal[k] = [Note(note) for note in v]

        self.map_normal: NoteData = NoteData(normal)

        hard = o["map_hard"]
        for k, v in hard.items():
            hard[k] = [Note(note) for note in v]

        self.map_hard: NoteData = NoteData(hard)

        master = o["map_master"]
        for k, v in master.items():
            master[k] = [Note(note) for note in v]

        self.map_master: NoteData = NoteData(master)


def fetch_song_data(song: str) -> SongData:
    meta = toml.load(f"{Conf.ROOT_DIR}/beatmaps/{song}/meta.toml")
    return SongData(meta)
