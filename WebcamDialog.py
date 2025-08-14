# WebcamDialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebcamDialog(QDialog):
    """Модальное окно для отображения веб-стрима."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Веб-камера: {host}")
        self.setGeometry(100, 100, 640, 480)
        self.setModal(True)

        layout = QVBoxLayout()
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(f"http://{host}/webcam/?action=stream"))
        layout.addWidget(self.web_view)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        self.setLayout(layout)
