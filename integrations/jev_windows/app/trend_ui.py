"""Windows relation-trend window for local CSVs and five example patterns."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

from core.trend import DEMO, demo, load_csv


class CandleCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.candles = ()
        self.setMinimumHeight(340)

    def set_candles(self, candles):
        self.candles = candles
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        if not self.candles:
            return
        values = [v for c in self.candles for v in (c.low, c.high)]
        low, high = min(values), max(values)
        padding = max(2, (high - low) * .15)
        low -= padding; high += padding
        top, bottom = 28, self.height() - 48
        left, right = 52, self.width() - 20
        def y(value): return bottom - (value - low) / (high - low) * (bottom - top)
        painter.setPen(QPen(QColor("#e5ebe6"), 1))
        for n in range(5):
            yy = top + n * (bottom - top) / 4
            painter.drawLine(left, int(yy), right, int(yy))
        span = (right - left) / max(1, len(self.candles))
        for i, candle in enumerate(self.candles):
            x = left + (i + .5) * span
            color = QColor("#29775d" if candle.close >= candle.open else "#c7755c")
            painter.setPen(QPen(color, 2))
            painter.drawLine(int(x), int(y(candle.high)), int(x), int(y(candle.low)))
            width = min(30, max(5, span * .55))
            a, b = y(candle.open), y(candle.close)
            painter.fillRect(QRectF(x - width / 2, min(a, b), width, max(2, abs(a - b))), color)
            if i % max(1, len(self.candles) // 8) == 0:
                painter.setPen(QColor("#6a766f"))
                painter.drawText(int(x - 24), self.height() - 18, 70, 16,
                                 Qt.AlignLeft, candle.date[-5:])
        painter.end()


class TrendWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("狗头军师 · 关系走势 K 线")
        self.resize(780, 500)
        root = QVBoxLayout(self)
        heading = QLabel("关系走势 K 线")
        heading.setStyleSheet("font-size:24px;font-weight:600;color:#294438")
        root.addWidget(heading)
        root.addWidget(QLabel("选择示例走势，或导入带 timestamp,sender,message 列的聊天 CSV。"))
        row = QHBoxLayout()
        self.case = QComboBox()
        self.case.addItems(list(DEMO))
        self.case.currentTextChanged.connect(self.load_demo)
        row.addWidget(self.case)
        button = QPushButton("导入聊天 CSV")
        button.clicked.connect(self.import_csv)
        row.addWidget(button)
        root.addLayout(row)
        self.canvas = CandleCanvas()
        root.addWidget(self.canvas)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(QLabel("导入数据只按每日消息方向净差计算；图形不代表爱意、回复率或关系成功率。"))
        self.load_demo(self.case.currentText())

    def load_demo(self, name):
        if name:
            self.canvas.set_candles(demo(name))
            self.status.setText(f"{name} · 示例走势；转折仍需结合实际聊天事件判断。")

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入聊天 CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            candles = load_csv(path)
            self.canvas.set_candles(candles)
            self.status.setText(f"已导入 {len(candles)} 个聊天日期 · 本地计算消息净差。")
        except ValueError as exc:
            self.status.setText(str(exc))
