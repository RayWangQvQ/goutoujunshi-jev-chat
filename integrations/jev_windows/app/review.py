"""Human review of OCR text and speaker side before a model request."""
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QVBoxLayout)


class ReviewDialog(QDialog):
    def __init__(self, title: str, messages: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"核对本轮对话 · {title}")
        self.resize(620, 520)
        root = QVBoxLayout(self)
        heading = QLabel("核对原文和说话人，再交给模型分析")
        heading.setStyleSheet("font-size:18px;font-weight:600;color:#294438")
        root.addWidget(heading)
        root.addWidget(QLabel("每行以“我：”或“对方：”开头；OCR 可能认错字、错分边或漏行。"))
        self.editor = QPlainTextEdit()
        self.editor.setPlainText("\n".join(
            ("我" if row[0] == "me" else "对方") + "：" + str(row[1])
            for row in messages))
        root.addWidget(self.editor)
        actions = QHBoxLayout()
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        actions.addStretch()
        confirm = QPushButton("确认并分析")
        confirm.clicked.connect(self._confirm)
        actions.addWidget(confirm)
        root.addLayout(actions)
        self.messages = []

    def _confirm(self):
        rows = [row.strip() for row in self.editor.toPlainText().splitlines() if row.strip()]
        parsed = []
        for row in rows:
            if row.startswith("我："):
                who, content = "me", row[2:].strip()
            elif row.startswith("对方："):
                who, content = "her", row[3:].strip()
            else:
                QMessageBox.warning(self, "请核对", "每行须以“我：”或“对方：”开头。")
                return
            if not content:
                QMessageBox.warning(self, "请核对", "请删除空消息，或补上正文。")
                return
            parsed.append((who, content))
        if not parsed or len(parsed) > 60:
            QMessageBox.warning(self, "请核对", "请保留 1 到 60 条相关消息。")
            return
        self.messages = parsed
        self.accept()
