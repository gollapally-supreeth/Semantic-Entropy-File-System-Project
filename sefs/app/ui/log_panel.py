from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import pyqtSlot
import datetime

class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

    @pyqtSlot(str)
    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.text_edit.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
