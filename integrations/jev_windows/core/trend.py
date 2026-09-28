"""Local chat-message balance candles. No model call and no relationship score."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Candle:
    date: str
    open: int
    high: int
    low: int
    close: int


DEMO = {
    "双向升温": [(50, 56, 48, 54), (54, 64, 53, 61), (61, 72, 60, 70),
                 (70, 76, 68, 74), (74, 82, 72, 79), (79, 86, 77, 83)],
    "热聊后降温": [(50, 59, 48, 57), (57, 65, 55, 63), (63, 66, 58, 60),
                   (60, 63, 51, 54), (54, 56, 43, 46), (46, 52, 44, 49),
                   (49, 50, 45, 47), (47, 49, 34, 38)],
    "冲突后修复": [(55, 61, 53, 59), (59, 61, 28, 36), (36, 49, 34, 45),
                   (45, 63, 43, 60), (60, 68, 58, 65)],
    "忙但仍兑现": [(50, 55, 48, 53), (53, 62, 51, 59), (59, 60, 55, 58),
                   (58, 60, 55, 58), (58, 65, 56, 63), (63, 76, 61, 73),
                   (73, 80, 71, 77)],
    "明确边界后收线": [(50, 54, 48, 51), (51, 53, 38, 41), (41, 42, 35, 37)],
}


def demo(name: str) -> tuple[Candle, ...]:
    if name not in DEMO:
        raise ValueError("没有这个示例走势")
    return tuple(Candle(f"示例 {i + 1}", *row) for i, row in enumerate(DEMO[name]))


def load_csv(path: str | Path) -> tuple[Candle, ...]:
    """timestamp,sender,message; sender is me/other, sorted ascending."""
    source = Path(path)
    if source.suffix.lower() != ".csv" or not source.is_file():
        raise ValueError("请选择聊天 CSV 文件")
    if source.stat().st_size > 4_000_000:
        raise ValueError("CSV 超过 4 MB，请缩小时间范围")
    balance = 0
    rows = []
    previous = None
    count = 0
    try:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"timestamp", "sender", "message"}.issubset(reader.fieldnames):
                raise ValueError("CSV 需要 timestamp,sender,message 三列")
            for item in reader:
                count += 1
                if count > 20_000:
                    raise ValueError("聊天超过 20000 条，请缩小范围")
                at = datetime.fromisoformat((item.get("timestamp") or "").strip())
                if previous and at < previous:
                    raise ValueError("聊天时间必须按升序排列")
                previous = at
                sender = (item.get("sender") or "").strip()
                if sender not in ("me", "other") or not (item.get("message") or "").strip():
                    raise ValueError("请核对 sender（me／other）和消息正文")
                date = at.date().isoformat()
                if not rows or rows[-1].date != date:
                    rows.append(Candle(date, balance, balance, balance, balance))
                balance += 1 if sender == "other" else -1
                old = rows[-1]
                rows[-1] = Candle(date, old.open, max(old.high, balance),
                                  min(old.low, balance), balance)
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("CSV 无法读取，请检查编码和列名") from exc
    if not rows:
        raise ValueError("CSV 没有聊天记录")
    return tuple(rows)
