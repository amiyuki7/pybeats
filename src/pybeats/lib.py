from __future__ import annotations

import colorama
from .conf import Conf
import toml
from typing import Any, Dict, List
from collections import OrderedDict


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
            vocaloid_en: str = __o["vocaloid_en"]
            vocaloid_avatar: str = __o["vocaloid_avatar"]
            cover: str = __o["cover"]
            cover_en: str = __o["cover_en"]
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
            expert: int = __o["expert"]
            master: int = __o["master"]

        self.difficulty = Difficulty

        notes = o["notes"]

        for k, v in notes.items():
            notes[k] = [Note(note) for note in v]

        self.note_data: NoteData = NoteData(notes)


def fetch_song_data(song: str) -> SongData:
    meta = toml.load(f"{Conf.ROOT_DIR}/beatmaps/{song}/meta.toml")
    return SongData(meta)


# from pprint import pprint
#
# song_data = fetch_song_data("ド屑")
# note_data = song_data.note_data
#
# pprint(note_data.next_note_beat)
# pprint(note_data.notes[note_data.next_note_beat][0].__dict__)
# # pprint(note_data.notes[note_data.next_note_beat][0].__dict__)
# # pprint(note_data.notes[note_data.next_note_beat][0].__dict__)
# # pprint(note_data.notes[note_data.next_note_beat][0].__dict__)
