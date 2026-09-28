# -*- coding: utf-8 -*-
"""Headless construction smoke test for the packaged Qt views."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.overlay import Overlay
from app.review import ReviewDialog
from app.trend_ui import TrendWindow


def main():
    overlay = Overlay(on_fill=lambda _text: None, result_of=lambda _title: None)
    overlay.open_settings()
    overlay._back_home()
    overlay.show({"candidates": ["好，周六见", "行，周六见"], "best_index": 0,
                  "scores": [.6, .4], "goutou": {"intent": "可能愿意继续聊",
                  "action": "先承接", "facts": ["对方说周六见"]}})
    review = ReviewDialog("测试会话", [("me", "在吗"), ("her", "在")], overlay.win)
    assert review.editor.toPlainText().count("：") == 2
    trend = TrendWindow()
    assert trend.canvas.candles
    trend.close()
    review.close()
    overlay.win.close()
    print("windows ui ok")


if __name__ == "__main__":
    main()
