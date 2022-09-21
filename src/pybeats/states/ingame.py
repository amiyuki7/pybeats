from __future__ import annotations

import time
from math import floor
from typing import TYPE_CHECKING, List, Tuple

import pygame as pg
from pygame.rect import Rect
from pygame.surface import Surface
from pygame import font

from pybeats.lib import Note

from ..conf import Conf

if TYPE_CHECKING:
    from ..app import App

from ..app import State

ROOT_DIR = Conf.ROOT_DIR


class Lane:
    def __init__(self, ctx: InGame, xpos: int, id: int) -> None:
        self.ctx = ctx
        self.id = id
        self.rect: Rect = Rect(xpos, 0, self.ctx.lane_width, self.ctx.ctx.SCREEN_HEIGHT)
        self.surface: Surface = Surface(self.rect.size)
        self.surface.fill((0, 0, 0))
        self.surface.set_alpha(120)

        scale = self.ctx.ctx.SCREEN_HEIGHT // 35
        self.font = font.Font(f"{ROOT_DIR}/fonts/Mylodon-Light.otf", scale)
        self.key_hint = self.font.render(Conf.KEYBINDS[f"lane{id}"], True, (255, 255, 255))
        self.key_hint_rect = self.key_hint.get_rect()
        self.key_hint_rect.centerx = self.rect.centerx
        self.key_hint_rect.y = floor(self.ctx.ctx.SCREEN_HEIGHT * 34.4 / 40)

    def draw(self) -> None:
        pg.draw.rect(self.surface, (130, 130, 130), (0, 0, self.rect.width, self.rect.height), 5)
        # self.surface.set_alpha(120)
        self.ctx.ctx.Display.blit(self.surface, self.rect)


class NoteObject:
    __slots__ = ["ctx", "surface", "rect", "remdist", "lane", "width", "type", "length", "pair", "down", "alive"]

    def __init__(self, ctx: InGame, note: Note) -> None:
        self.ctx = ctx
        self.lane = self.ctx.lanes[note.lane - 1]
        self.width = note.width

        self.type = note.type

        if self.type == "hr":
            if note.pair in self.ctx.dead_sliders:
                self.type = "t"

        self.length = note.length
        self.pair = note.pair
        self.down = False
        self.alive = True

        if self.type == "h":
            assert self.ctx.ctx.conductor
            self.surface: Surface = Surface(
                (
                    self.lane.rect.width * self.width - self.ctx.lane_border_width * (2 + self.width - 1),
                    # Calculates the note's height
                    (60 * self.ctx.relative_speed * self.ctx.ctx.conductor.sec_per_beat * note.length),
                )
            )
            self.surface.fill((148, 236, 150))
            self.surface.set_alpha(210)
            self.rect: Rect = self.surface.get_rect()
            self.rect.left = self.lane.rect.left + self.ctx.lane_border_width
            self.rect.bottom = self.ctx.note_height
        else:
            self.surface: Surface = Surface(
                (
                    self.lane.rect.width * self.width - self.ctx.lane_border_width * (2 + self.width - 1),
                    self.ctx.note_height,
                )
            )

            self.surface.fill((177, 156, 217))
            if self.type == "hr":
                self.surface.fill((48, 136, 50))

            self.surface.set_alpha(210)
            self.rect: Rect = self.surface.get_rect()
            self.rect.left = self.lane.rect.left + self.ctx.lane_border_width
            self.rect.y = 0

            self.remdist: int = self.ctx.hit_area_rect.centery - self.rect.centery

    def draw(self) -> None:
        self.ctx.ctx.Display.blit(self.surface, self.rect)


class InGame(State):
    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg: Surface = self.ctx.image_cache["assets/ingame.jpg"]
        self.bg = pg.transform.scale(self.bg, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.note_height = floor(self.ctx.SCREEN_HEIGHT * 120 / 1920)

        self.lane_border_width = 5
        self.lane_width_raw = 140
        self.lane_width = floor(self.ctx.SCREEN_WIDTH * self.lane_width_raw / 1920)

        self.lanes: List[Lane] = []

        for i in range(8):
            left_margin = (
                floor(self.ctx.SCREEN_WIDTH * ((1920 - self.lane_width_raw * 8) / 2) / 1920)
                + (8 * self.lane_border_width) // 2
            )
            self.lanes.append(Lane(self, left_margin + (i * self.lane_width) - (i * self.lane_border_width), id=i))

        self.hit_area = Surface((self.lanes[-1].rect.right - self.lanes[0].rect.left, self.note_height))
        self.hit_area.fill((0, 0, 0))
        self.hit_area.set_alpha(170)
        self.hit_area_rect = self.hit_area.get_rect()
        self.hit_area_rect.x = self.lanes[0].rect.x
        self.hit_area_rect.y = floor(self.ctx.SCREEN_HEIGHT - self.note_height * 2.5)

        self.bottom_overlay = Surface(
            (self.hit_area_rect.width - self.lane_border_width * 2, self.ctx.SCREEN_HEIGHT - self.hit_area_rect.bottom)
        )
        self.bottom_overlay.fill((0, 0, 0))
        self.bottom_overlay_rect = self.bottom_overlay.get_rect()
        self.bottom_overlay_rect.centerx = self.hit_area_rect.centerx
        self.bottom_overlay_rect.y = self.hit_area_rect.bottom

        self.ctx.mixer.play_sfx(self.ctx.sfx.lead_pause, self.ctx.LeadPauseChannel)
        self.finished_pause = False
        self.start_pause = time.time()

        self.playing = False
        self.song_over = False

        assert self.ctx.conductor
        self.ctx.mixer.load(f"{ROOT_DIR}/beatmaps/{self.ctx.conductor.song}/{self.ctx.conductor.song}.mp3")

        self.travel_dist = self.hit_area_rect.centery - self.note_height // 2
        self.note_speed = 4
        self.new_note_speed = self.note_speed + 3
        # 457 is not a random number; it's the travel distance for a 960x540 window
        self.relative_speed = floor(self.travel_dist / (457 / self.new_note_speed))
        self.time_frames = self.travel_dist / self.relative_speed

        # self.notes: List[NoteObject] = []
        self.notes: List[List[NoteObject]] = []
        self.next_note_beat: int = 0

        self.start_time = time.time()
        self.song_start_time = 0

        self.spawned_first_note = False

        self.dead_sliders: List[int] = []

        self.combo = 0

    def spawn_note(self) -> None:
        assert self.ctx.conductor

        if not self.spawned_first_note:
            self.spawned_first_note = True
            self.song_start_time = time.time() - self.start_time
            self.first_beat = int(self.ctx.conductor.next_note_beat)
            notes = self.ctx.conductor.note_data.notes[str(self.first_beat)]
            notes_mapped: List[NoteObject] = [NoteObject(self, note) for note in notes]
            self.notes.append(notes_mapped)
            self.next_note_beat = int(self.ctx.conductor.next_note_beat)

        # If it's time to spawn another note
        # NOTE: The *2.1 is a future calibration setting
        if (
            time.time() - self.start_time + self.ctx.conductor.sec_per_beat * 2.1
        ) >= self.song_start_time + self.next_note_beat * self.ctx.conductor.sec_per_beat:
            notes = self.ctx.conductor.note_data.notes[str(self.next_note_beat)]
            notes_mapped: List[NoteObject] = [NoteObject(self, note) for note in notes]
            self.notes.append(notes_mapped)

            # Reached the last note, stop spawning
            if self.next_note_beat == int(self.ctx.conductor.final_note_beat):
                self.song_over = True
                return

            self.next_note_beat = int(self.ctx.conductor.next_note_beat)

        """
        It takes time_frames/60 seconds for a note to get from spawn to bottom
        Thus, Spawn the note exactly (time_frames)/60 s before the beat hits
        * Keep an elapsed time, and calculate parts off that
        * Time to spawn = Initial time + next beat-to-sec
        """

    def check_key(self, group: List[NoteObject], expected: List[Tuple[int]], grade: str) -> None:
        key_state = self.ctx.lanes_state

        pressed_notes: List[bool] = [False for _ in range(len(group))]

        for idx, keys in enumerate(expected):
            for key in keys:
                if key_state[key]:
                    pressed_notes[idx] = True

        # print(pressed_notes)

        hit_sounds = []

        for idx, b in enumerate(pressed_notes):
            if b:
                target = group[idx]

                if target.type == "h":
                    if target.alive and not target.down:
                        target.down = True
                        hit_sounds.append(target)
                        for lane in range(target.lane.id, target.lane.id + target.width):
                            self.lanes[lane].surface.set_alpha(230)
                else:

                    hit_sounds.append(target)
                    for lane in range(target.lane.id, target.lane.id + target.width):
                        self.lanes[lane].surface.set_alpha(230)

                    group[idx] = None  # type: ignore

                print(grade)

        assert self.ctx.conductor
        self.ctx.conductor.play_hit_sounds(hit_sounds, grade)

        if all(note is None for note in group):
            self.notes.remove(group)

    def update(self) -> None:
        assert self.ctx.conductor

        # Waiting 5 seconds before the song starts, but of course note spawning will start just before 5 seconds
        if 5 - (time.time() - self.start_time) <= (self.time_frames / 60) and not self.song_over:
            self.spawn_note()

        for idx, b in enumerate(self.ctx.lanes_state):
            if b and self.lanes[idx].surface.get_alpha() == 120:
                # if self.lanes[idx].surface.get_alpha() == 120:
                self.lanes[idx].surface.set_alpha(230)
            else:
                # self.lanes[idx].surface.set_alpha(120)
                if self.lanes[idx].surface.get_alpha() != 120:
                    self.lanes[idx].surface.set_alpha(self.lanes[idx].surface.get_alpha() - 5)  # type: ignore

        for group in self.notes:
            for note in group:
                if note:

                    if note.type == "hr":
                        if note.pair in self.dead_sliders:
                            note.type = "t"
                            note.surface.fill((177, 156, 217))

                    ## Move notes ##
                    if group[0] == None:
                        group[0] = note

                    if note == group[0]:
                        if note.type == "h":
                            note.rect.y += self.relative_speed
                        else:
                            if (
                                note.rect.y + self.relative_speed > self.hit_area_rect.y
                                and note.rect.top < self.hit_area_rect.top
                            ):
                                note.rect.y += self.hit_area_rect.y - note.rect.y
                            else:
                                note.rect.y += self.relative_speed
                    else:
                        note.rect.y = group[0].rect.y

                    ## Check presses and evaluate a score ##

                    expected_lanes: List[Tuple[int]] = []

                    if group in self.notes:
                        for obj in self.notes[0]:
                            if obj:
                                expected_lanes.append(tuple(x for x in range(obj.lane.id, obj.lane.id + obj.width)))

                        if note.type != "h" and note.type != "hr":
                            # if note.type != "h":
                            if (
                                (
                                    note.rect.top < self.hit_area_rect.top
                                    and note.rect.top + 2 * self.relative_speed >= self.hit_area_rect.top
                                )
                                or (
                                    note.rect.bottom > self.hit_area_rect.bottom
                                    and note.rect.bottom - 2 * self.relative_speed <= self.hit_area_rect.bottom
                                )
                                or note.rect.centery == self.hit_area_rect.centery
                            ):
                                # Perfect
                                self.check_key(group, expected_lanes, "PERFECT")

                            elif (
                                note.rect.top < self.hit_area_rect.top
                                and note.rect.top + 4 * self.relative_speed >= self.hit_area_rect.top
                            ) or (
                                note.rect.bottom > self.hit_area_rect.bottom
                                and note.rect.bottom - 4 * self.relative_speed <= self.hit_area_rect.bottom
                            ):
                                # Great
                                self.check_key(group, expected_lanes, "GREAT")

                            elif (
                                note.rect.top < self.hit_area_rect.top
                                and note.rect.top + 6 * self.relative_speed >= self.hit_area_rect.top
                            ):
                                # Early
                                self.check_key(group, expected_lanes, "EARlY")

                        elif note.type == "h":
                            # else:
                            if note.alive and not note.down:
                                # Detect the initial hit on the slider head
                                if (
                                    (
                                        note.rect.bottom - self.note_height < self.hit_area_rect.top
                                        and note.rect.bottom - self.note_height + 2 * self.relative_speed
                                        >= self.hit_area_rect.top
                                    )
                                    or (
                                        note.rect.bottom > self.hit_area_rect.bottom
                                        and note.rect.bottom - 2 * self.relative_speed <= self.hit_area_rect.bottom
                                    )
                                    or (note.rect.bottom - (note.rect.bottom - self.note_height) // 2)
                                    == self.hit_area_rect.centery
                                ):
                                    # Perfect
                                    self.check_key(group, expected_lanes, "PERFECT")
                                    pass
                                elif (
                                    note.rect.bottom - self.note_height < self.hit_area_rect.top
                                    and note.rect.bottom - self.note_height + 4 * self.relative_speed
                                    >= self.hit_area_rect.top
                                ) or (
                                    note.rect.bottom > self.hit_area_rect.bottom
                                    and note.rect.bottom - 4 * self.relative_speed <= self.hit_area_rect.bottom
                                ):
                                    # Great
                                    self.check_key(group, expected_lanes, "GREAT")
                                elif (
                                    note.rect.bottom - self.note_height < self.hit_area_rect.top
                                    and note.rect.bottom - self.note_height + 6 * self.relative_speed
                                    > self.hit_area_rect.top
                                ):
                                    # Early
                                    self.check_key(group, expected_lanes, "EARLY")
                                elif note.rect.bottom - self.note_height > self.hit_area_rect.bottom:
                                    print("MISS")
                                    note.alive = False
                                    note.surface.fill((200, 200, 200))
                                    note.surface.set_alpha(100)
                                    self.dead_sliders.append(note.pair)

                            if (
                                note.down
                                and note.alive
                                and (note.rect.top + 6 * self.relative_speed < self.hit_area_rect.top)
                            ):
                                key_state = self.ctx.lanes_state

                                still_down = False

                                slider_lanes = list(range(note.lane.id, note.lane.id + note.width))
                                # for keys in expected_lanes:
                                #     for key in keys:
                                #         if key_state[key]:
                                #             still_down = True
                                for key in slider_lanes:
                                    if key_state[key]:
                                        still_down = True

                                if not still_down:
                                    # Break combo
                                    print("Slider MISS")
                                    note.alive = False
                                    note.surface.fill((200, 200, 200))
                                    note.surface.set_alpha(100)
                                    self.dead_sliders.append(note.pair)

                        elif note.type == "hr":
                            if (
                                (
                                    note.rect.top < self.hit_area_rect.top
                                    and note.rect.top + 2 * self.relative_speed >= self.hit_area_rect.top
                                )
                                or (
                                    note.rect.bottom > self.hit_area_rect.bottom
                                    and note.rect.bottom - 2 * self.relative_speed <= self.hit_area_rect.bottom
                                )
                                or note.rect.centery == self.hit_area_rect.centery
                            ):
                                # PERFECT
                                key_state = self.ctx.lanes_state

                                release_lanes = list(range(note.lane.id, note.lane.id + note.width))

                                released = True

                                for key in release_lanes:
                                    if key_state[key]:
                                        released = False

                                if released:
                                    for lane in range(note.lane.id, note.lane.id + note.width):
                                        self.lanes[lane].surface.set_alpha(200)

                                    self.ctx.conductor.play_hit_sounds([note], "PERFECT")
                                    # group[0] = None  # type: ignore

                                    for idx, _note in enumerate(group):
                                        if note == _note:
                                            group[idx] = None  # type: ignore

                                if all(note is None for note in group):
                                    self.notes.remove(group)

                            elif (
                                note.rect.top < self.hit_area_rect.top
                                and note.rect.top + 4 * self.relative_speed >= self.hit_area_rect.top
                            ) or (
                                note.rect.bottom > self.hit_area_rect.bottom
                                and note.rect.bottom - 4 * self.relative_speed <= self.hit_area_rect.bottom
                            ):
                                # great
                                key_state = self.ctx.lanes_state

                                release_lanes = list(range(note.lane.id, note.lane.id + note.width))

                                released = True

                                for key in release_lanes:
                                    if key_state[key]:
                                        released = False

                                if released:
                                    for lane in range(note.lane.id, note.lane.id + note.width):
                                        self.lanes[lane].surface.set_alpha(200)

                                    self.ctx.conductor.play_hit_sounds([note], "PERFECT")
                                    # group[0] = None  # type: ignore

                                    for idx, _note in enumerate(group):
                                        if note == _note:
                                            group[idx] = None  # type: ignore

                                if all(note is None for note in group):
                                    self.notes.remove(group)
                            elif (
                                note.rect.top < self.hit_area_rect.top
                                and note.rect.top + 6 * self.relative_speed >= self.hit_area_rect.top
                            ):
                                # early
                                key_state = self.ctx.lanes_state

                                release_lanes = list(range(note.lane.id, note.lane.id + note.width))

                                released = True

                                for key in release_lanes:
                                    if key_state[key]:
                                        released = False

                                if released:
                                    for lane in range(note.lane.id, note.lane.id + note.width):
                                        self.lanes[lane].surface.set_alpha(200)

                                    self.ctx.conductor.play_hit_sounds([note], "PERFECT")
                                    # group[0] = None  # type: ignore

                                    for idx, _note in enumerate(group):
                                        if note == _note:
                                            group[idx] = None  # type: ignore

                                if all(note is None for note in group):
                                    self.notes.remove(group)

                    # Should be for notes that are not of type h | hr
                    if note:
                        # if note.rect.top > self.hit_area_rect.bottom and note.type != "h":
                        if note.rect.top > self.hit_area_rect.bottom:
                            # Missed
                            if group in self.notes:
                                self.notes.remove(group)

                                if not note.type == "h" and note.alive:
                                    print("MISS MISS MISS", note.type)

                        # Might remove this field if it proves itself for future redundancy
                        note.remdist = self.hit_area_rect.centery - note.rect.centery

        if not self.playing:
            if not len(self.notes) > 0:
                return
            # If first note's remaining distance needs (first beat * bps) more time to reach the hit area
            if self.notes[0][0].remdist / self.relative_speed / 60 <= self.ctx.conductor.sec_per_beat * self.first_beat:
                self.ctx.mixer.toggle_pause()
                self.playing = True

        if self.playing:
            self.ctx.conductor.update()

    def draw(self) -> None:
        self.ctx.Display.blit(self.bg, (0, 0))

        for lane in self.lanes:
            lane.draw()

        pg.draw.rect(self.hit_area, (200, 100, 220), (0, 0, self.hit_area_rect.width, self.hit_area_rect.height), 5)
        self.ctx.Display.blit(self.hit_area, self.hit_area_rect)

        for group in self.notes:
            for note in group:
                if note:
                    note.draw()

        self.ctx.Display.blit(self.bottom_overlay, self.bottom_overlay_rect)

        for lane in self.lanes:
            self.ctx.Display.blit(lane.key_hint, lane.key_hint_rect)
