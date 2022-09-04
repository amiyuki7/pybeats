from __future__ import annotations

import time
from math import floor
from typing import TYPE_CHECKING, List, no_type_check

import pygame as pg
from pygame.rect import Rect
from pygame.surface import Surface

from ..conf import Conf

if TYPE_CHECKING:
    from ..app import App

from ..app import State

ROOT_DIR = Conf.ROOT_DIR


class Lane:
    def __init__(self, ctx: InGame, xpos: int) -> None:
        self.ctx = ctx
        self.rect: Rect = Rect(xpos, 0, floor(self.ctx.ctx.SCREEN_WIDTH * 180 / 1920), self.ctx.ctx.SCREEN_HEIGHT)
        self.surface: Surface = Surface(self.rect.size)
        self.surface.fill((0, 0, 0))
        self.surface.set_alpha(120)

    def draw(self) -> None:
        pg.draw.rect(self.surface, (130, 130, 130), (0, 0, self.rect.width, self.rect.height), 5)
        self.surface.set_alpha(120)
        self.ctx.ctx.Display.blit(self.surface, self.rect)


class NoteObject:
    def __init__(self, ctx: InGame, lane: Lane) -> None:
        self.ctx = ctx
        self.surface: Surface = Surface((lane.rect.width - self.ctx.lane_border_width * 2, self.ctx.note_height))
        self.surface.fill((255, 0, 0))
        self.rect: Rect = self.surface.get_rect()
        self.rect.centerx = lane.rect.centerx
        self.rect.y = 0

    def draw(self) -> None:
        self.ctx.ctx.Display.blit(self.surface, self.rect)


class InGame(State):
    notes: List[NoteObject] = []

    def __init__(self, ctx: App) -> None:
        super().__init__(ctx)

        self.bg: Surface = self.ctx.image_cache["assets/ingame.jpg"]
        self.bg = pg.transform.scale(self.bg, (self.ctx.SCREEN_WIDTH, self.ctx.SCREEN_HEIGHT)).convert_alpha()
        self.bg.set_alpha(180)

        self.note_height = floor(self.ctx.SCREEN_HEIGHT * 120 / 1920)

        self.lane_border_width = 5

        self.lanes: List[Lane] = []

        for i in range(8):
            left_margin = floor(self.ctx.SCREEN_WIDTH * 240 / 1920) + (8 * self.lane_border_width) // 2
            self.lanes.append(
                Lane(
                    self,
                    left_margin + (floor(i * self.ctx.SCREEN_WIDTH * 180 / 1920)) - i * self.lane_border_width,
                )
            )

        self.hit_area = Surface((self.lanes[-1].rect.right - self.lanes[0].rect.left, self.note_height))
        self.hit_area.fill((0, 0, 0))
        self.hit_area.set_alpha(170)
        self.hit_area_rect = self.hit_area.get_rect()
        self.hit_area_rect.x = self.lanes[0].rect.x
        self.hit_area_rect.y = floor(self.ctx.SCREEN_HEIGHT - self.note_height * 2.5)

        self.ctx.mixer.play_sfx(self.ctx.sfx.lead_pause, self.ctx.LeadPauseChannel)
        self.finished_pause = False
        self.start_pause = time.time()

        self.playing = False

        assert self.ctx.conductor
        self.ctx.mixer.load(f"{ROOT_DIR}/beatmaps/{self.ctx.conductor.song}/{self.ctx.conductor.song}.mp3")

        self.travel_dist = self.hit_area_rect.centery - self.note_height // 2
        self.note_speed = 3
        self.new_note_speed = self.note_speed + 3
        # 457 is not a random number; it's the travel distance for a 960x540 window
        self.relative_speed = floor(self.travel_dist / (457 / self.new_note_speed))
        self.time_frames = self.travel_dist / self.relative_speed

        self.note_a = NoteObject(self, self.lanes[2])

    def update(self) -> None:
        assert self.ctx.conductor
        # Wait for a while so to not overwhelm the player (maybe control this by playing a 5 second silent track)
        # Start spawning notes
        # Calculate time it takes for the note to drop down to the hit area (time = distance / speed)
        # Start music buffering at the perfect time

        # Do nothing if the leading 5 seconds is not over
        # But i also need to get the perfect ms to start spawning notes!
        if self.ctx.LeadPauseChannel.get_busy():
            return

        if not self.finished_pause:
            self.finished_pause = True
            # Theoretically should be 5 seconds
            print(time.time() - self.start_pause)

        if not self.playing:
            self.ctx.mixer.toggle_pause()
            self.playing = True

        if self.playing:
            self.ctx.conductor.update()

            if self.note_a.rect.centery + self.note_speed > self.hit_area_rect.centery:
                self.note_a.rect.y += self.hit_area_rect.centery - self.note_a.rect.centery

            if not self.note_a.rect.centery == self.hit_area_rect.centery:
                self.note_a.rect.y += self.relative_speed

    def draw(self) -> None:
        self.ctx.Display.blit(self.bg, (0, 0))

        for lane in self.lanes:
            lane.draw()

        pg.draw.rect(self.hit_area, (200, 100, 220), (0, 0, self.hit_area_rect.width, self.hit_area_rect.height), 5)
        self.ctx.Display.blit(self.hit_area, self.hit_area_rect)

        self.note_a.draw()
