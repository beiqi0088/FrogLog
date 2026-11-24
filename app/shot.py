# -*- coding: utf-8 -*-
"""shot.py - 无头渲染各页面，导出 PNG（用于回归检查/预览）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app import MainWindow

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(430, 880)
    win.show()
    app.processEvents()

    def snap(name):
        win.toast_label.hide()
        for _ in range(3):
            app.processEvents()
        win.repaint()
        win.grab().save(os.path.join(OUT, f"{name}.png"))
        print("saved", name)

    snap("01-today")
    win.show_page("library"); snap("02-library")
    import pages.library as L3
    lib = win.stack.currentWidget()
    round_rows = lib.findChildren(L3.EntityRow)
    if round_rows:
        QTest.mouseClick(round_rows[0], Qt.LeftButton)
        app.processEvents()
        snap("23-round")
        win.show_page("library")
        app.processEvents()
    win.show_page("deck", deck_id="renxing"); snap("03-deck")
    # 存档：把第二个卡组存起来，页面上出现「存档」分区
    deck_page = win.stack.currentWidget()
    # 选中一个卡组
    if deck_page._rows:
        deck_page._select_group(deck_page._rows[0].property("group"), True)
        app.processEvents()
        snap("22-group-selected")
        deck_page = win.stack.currentWidget()
    d0 = win.store.deck("renxing")
    d0["archived_groups"] = []
    d0["completed_groups"] = []
    win.store.save()
    deck_page.build()
    app.processEvents()
    if len(deck_page._swipes) > 1:
        deck_page._on_action(deck_page._swipes[1].property("group"), "archive")
        app.processEvents()
        snap("20-deck-archived")
    # 左滑露出 存档 / 完成 / 删除
    if deck_page._swipes:
        row = deck_page._swipes[0]
        row.set_offset(row.panel_w)
        app.processEvents()
        snap("21-swipe-actions")
    d0["archived_groups"] = []
    d0["completed_groups"] = []
    win.store.save()
    win.show_page("plan"); snap("04-plan")
    win.show_page("insights"); snap("05-insights")
    win.show_page("settings"); snap("06-settings")
    win.show_page("backup"); snap("26-backup")
    win.show_page("memo"); snap("07-memo")
    win.show_page("split"); snap("08-split")
    win.show_page("templates", deck_id="renxing"); snap("09-templates")
    # 换模板 → 复习卡片同步换肤
    tpl_page = win.stack.currentWidget()
    tpl_page._pick("lime")
    qa0 = next((c for c in win.store.cards if c["type"] == "qa"), None)
    if qa0:
        win.start_review("renxing", single=qa0["id"])
        snap("19-review-lime")
    win.store.deck("renxing")["template"] = "sky"
    win.store.save()

    # 复习：问答 → 翻面 → 单选 → 多选
    store = win.store
    qa = next((c for c in store.cards if c["type"] == "qa"), None)
    if qa:
        win.start_review("renxing", single=qa["id"])
        snap("10-review-qa")
        win.stack.currentWidget()._reveal()
        snap("11-review-qa-answer")

    single = next((c for c in store.cards if c["type"] == "single"), None)
    if single:
        win.start_review("renxing", single=single["id"])
        snap("12-review-single")
        page = win.stack.currentWidget()
        import card_render as CR
        pills = page.findChildren(CR.OptionPill)
        QTest.mouseClick(pills[single["answer"][0]], Qt.LeftButton)
        app.processEvents()
        snap("13-review-single-judged")

    multi = next((c for c in store.cards if c["type"] == "multi"), None)
    if multi:
        win.start_review("renxing", single=multi["id"])
        p = win.stack.currentWidget()
        import card_render as CR
        pills = p.findChildren(CR.OptionPill)
        QTest.mouseClick(pills[0], Qt.LeftButton); app.processEvents()
        QTest.mouseClick(pills[1], Qt.LeftButton); app.processEvents()
        snap("14-review-multi-picked")
        p._submit(); snap("15-review-multi-judged")

    # 深色
    win.set_dark(True)
    win.show_page("today"); snap("16-dark-today")
    win.show_page("insights"); snap("17-dark-insights")
    win.set_dark(False)


if __name__ == "__main__":
    main()
