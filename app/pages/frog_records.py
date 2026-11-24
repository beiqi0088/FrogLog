# -*- coding: utf-8 -*-
"""pages/frog_records.py - 吃蛙记录（从「吃掉那只青蛙」右上角进入）。"""
from __future__ import annotations

from pages.base import Page
from pages.journey_panels import FrogTimelinePanel


class FrogRecordsPage(Page):
    """一整页的吃蛙时间线：按天分组、最新在上。"""

    def build(self):
        super().build()
        total = self.store.frogs_eaten()
        self.appbar("吃蛙记录", f"共 {total} 只青蛙", back=self.app.go_back)
        panel = FrogTimelinePanel(self)
        panel.show_header = False
        panel.build()
        self.add(panel)
        self.stretch()
