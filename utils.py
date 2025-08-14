# utils.py

import os
import platform
import subprocess
import socket
import logging
from config import ConfigManager

APP_NAME = "Moonraker Host Scanner"


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

    # Test host reachability
    try:
        socket.create_connection((host, 22), timeout=2)
        logger.debug(f"Host {host} is reachable on port 22")
    except (socket.timeout, socket.gaierror, ConnectionRefusedError) as e:
        logger.error(f"Host {host} is not reachable on port 22: {e}")
        raise RuntimeError(f"Cannot connect to {host}: Host is unreachable or SSH is not available")

    try:
        if platform.system() == "Windows":
            cmd = f'start cmd /k {ssh_command}'
            subprocess.run(cmd, shell=True, check=True)
        elif platform.system() == "Darwin":
            # Simplified AppleScript to open Terminal and run SSH
            cmd = f'osascript -e \'tell application "Terminal" to do script "{ssh_command}"\''
            subprocess.run(cmd, shell=True, check=True)
        else:
            cmd = f'x-terminal-emulator -e {ssh_command}'
            subprocess.run(cmd, shell=True, check=True)
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
