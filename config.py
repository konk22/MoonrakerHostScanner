# config.py

import os
import json
import logging


class ConfigManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_dir = os.path.expanduser("~/.moonraker_scanner")
        self.config_file = os.path.join(self.config_dir, "config.json")
        os.makedirs(self.config_dir, exist_ok=True)

    def load_config(self):
        """Загружает конфигурацию из файла."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def save_config(self, subnets, hosts, notification_states, ssh_user="", log_level="INFO", auto_refresh=True):
        """Сохраняет конфигурацию в файл."""
        config = {
            "subnets": subnets,
            "hosts": hosts,
            "notification_states": notification_states,
            "ssh_user": ssh_user,
            "log_level": log_level,
            "auto_refresh": auto_refresh
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.logger.debug("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    def clear_config(self):
        """Очищает файл конфигурации."""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            self.logger.debug("Configuration cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear config: {e}")

    def open_config_file(self):
        """Открывает файл конфигурации в текстовом редакторе."""
        try:
            import platform
            import subprocess
            if platform.system() == "Windows":
                os.startfile(self.config_file)
            elif platform.system() == "Darwin":
                subprocess.run(["open", self.config_file], check=True)
            else:
                subprocess.run(["xdg-open", self.config_file], check=True)
            self.logger.debug("Opened config file")
        except Exception as e:
            self.logger.error(f"Failed to open config file: {e}")
            raise RuntimeError(f"Cannot open config file: {e}")

    def save_current_config(self, main_window):
        """
        Сохраняет текущую конфигурацию, извлекая параметры из экземпляра MainWindow.
        """
        self.save_config(
            main_window.subnets,
            main_window.known_hosts,
            main_window.notification_states,
            main_window.ssh_user,
            main_window.log_level,
            main_window.auto_refresh
        )
