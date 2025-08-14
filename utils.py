# utils.py
from __future__ import annotations

import os
import platform
import subprocess
import socket
import logging
import shutil
from config import ConfigManager

APP_NAME = "Moonraker Host Scanner"

# --- Константы проекта ---
# Сеть / Moonraker
DEFAULT_MOONRAKER_PORT: int = 7125
DEFAULT_HTTP_TIMEOUT_S: int = 2
DEFAULT_SSH_PORT: int = 22
SCAN_CONNECT_TIMEOUT_S: int = 1

# Сканирование сети
KNOWN_HOSTS_WORKERS: int = 20
SUBNET_SCAN_WORKERS: int = 100

# UI интервалы
REFRESH_INTERVAL_MS: int = 5000
AUTO_REFRESH_INTERVAL_MS: int = 5000

# Прогресс сканирования
PROGRESS_EMIT_STEP: int = 32

# Состояния
STATE_OFFLINE: str = "Оффлайн"


def setup_logging(log_level="INFO"):
    """Настраивает логирование в файл и консоль."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Очищаем предыдущие обработчики
    logger.handlers.clear()

    config_manager = ConfigManager()
    log_file = os.path.join(config_manager.config_dir, "moonraker_scanner.log")

    # Обработчик для файла
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(file_handler)

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(console_handler)


def open_ssh_terminal(host, ssh_user=""):
    """Открывает SSH-терминал для указанного хоста."""
    logger = logging.getLogger(__name__)
    ssh_user = ssh_user or "pi"
    ssh_command = f"ssh {ssh_user}@{host}"

    # Ensure SSH client is available in PATH
    if shutil.which("ssh") is None:
        logger.error("SSH client not found in PATH")
        raise RuntimeError("SSH client not found. Please install OpenSSH and ensure 'ssh' is in PATH")

    # Test host reachability
    try:
        socket.create_connection((host, DEFAULT_SSH_PORT), timeout=2)
        logger.debug(f"Host {host} is reachable on port {DEFAULT_SSH_PORT}")
    except (socket.timeout, socket.gaierror, ConnectionRefusedError) as e:
        logger.error(f"Host {host} is not reachable on port {DEFAULT_SSH_PORT}: {e}")
        raise RuntimeError(f"Cannot connect to {host}: Host is unreachable or SSH is not available")

    try:
        system_name = platform.system()
        if system_name == "Windows":
            # Use cmd's built-in 'start' to open a new terminal window and run ssh
            cmd = f'start "" cmd /k {ssh_command}'
            subprocess.run(cmd, shell=True, check=True)
        elif system_name == "Darwin":
            # Activate Terminal and run SSH command in a new tab/window
            subprocess.run([
                "osascript",
                "-e", 'tell application "Terminal" to activate',
                "-e", f'tell application "Terminal" to do script "{ssh_command}"'
            ], check=True)
        else:
            # Linux / others: try multiple common terminal emulators
            candidates = []
            if shutil.which("x-terminal-emulator"):
                candidates.append(["x-terminal-emulator", "-e", "bash", "-lc", ssh_command])
            if shutil.which("gnome-terminal"):
                candidates.append(["gnome-terminal", "--", "bash", "-lc", ssh_command])
            if shutil.which("konsole"):
                candidates.append(["konsole", "-e", ssh_command])
            if shutil.which("xfce4-terminal"):
                candidates.append(["xfce4-terminal", "-e", ssh_command])
            if shutil.which("mate-terminal"):
                candidates.append(["mate-terminal", "-e", ssh_command])
            if shutil.which("xterm"):
                candidates.append(["xterm", "-e", ssh_command])
            if shutil.which("kitty"):
                candidates.append(["kitty", ssh_command])
            if shutil.which("alacritty"):
                candidates.append(["alacritty", "-e", ssh_command])

            last_error: Exception | None = None
            for candidate in candidates:
                try:
                    subprocess.run(candidate, check=True)
                    last_error = None
                    break
                except Exception as e:  # noqa: PERF203 - tried candidates sequentially
                    last_error = e
                    continue
            if last_error is not None:
                raise last_error
        logger.debug(f"Successfully executed SSH command: {ssh_command}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open SSH terminal for {host}: {e}")
        raise RuntimeError(f"SSH command failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error opening SSH terminal for {host}: {e}")
        raise RuntimeError(f"Unexpected SSH error: {e}")


LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


def set_log_level(level_name: str):
    level = LOG_LEVELS.get(level_name.upper(), logging.INFO)
    logging.getLogger().setLevel(level)


def resource_path(relative_path: str) -> str:
    """Возвращает абсолютный путь к ресурсу (работает и в PyInstaller)."""
    import sys
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
