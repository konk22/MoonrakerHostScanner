# main.py

import sys
from PyQt6.QtWidgets import QApplication
from ui import MainWindow
from utils import setup_logging


def main():
    app = QApplication(sys.argv)

    # Загружаем конфигурацию для получения уровня логирования
    from config import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.load_config()
    log_level = config.get("log_level", "INFO")

    # Настраиваем логирование
    setup_logging(log_level)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
