# network.py

import socket
import ipaddress
import requests
import logging
from cachetools import TTLCache
from utils import DEFAULT_MOONRAKER_PORT, DEFAULT_HTTP_TIMEOUT_S, SCAN_CONNECT_TIMEOUT_S


class NetworkUtils:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Кэш для get_printer_info с TTL 30 секунд
        self.printer_info_cache = TTLCache(maxsize=100, ttl=30)

    def get_local_subnet(self):
        """Получает подсеть локального компьютера."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('10.255.255.255', 1))
                ip = s.getsockname()[0]
                subnet = str(ipaddress.ip_network(f"{ip}/24", strict=False))
                self.logger.debug(f"Local subnet detected: {subnet}")
                return subnet
        except Exception as e:
            self.logger.error(f"Failed to get local subnet: {e}")
            return "192.168.1.0/24"  # Fallback subnet

    def scan_port(self, ip, port=DEFAULT_MOONRAKER_PORT, timeout=SCAN_CONNECT_TIMEOUT_S):
        """Проверяет, открыт ли порт на указанном IP."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((str(ip), port))
                self.logger.debug(f"Scanned {ip}:{port}, result={result}")
                return str(ip) if result == 0 else None
        except Exception as e:
            self.logger.debug(f"Scan port failed for {ip}: {e}")
            return None

    def get_printer_info(self, host):
        """Получает hostname и state принтера через API Moonraker с кэшированием."""
        if host in self.printer_info_cache:
            self.logger.debug(f"Retrieved printer info for {host} from cache")
            return self.printer_info_cache[host]

        hostname = "Неизвестно"
        state = "Недоступен"
        try:
            response = requests.get(f"http://{host}:{DEFAULT_MOONRAKER_PORT}/printer/info", timeout=DEFAULT_HTTP_TIMEOUT_S)
            if response.status_code == 200:
                data = response.json()
                hostname = data.get("result", {}).get("hostname", "Неизвестно")

            response = requests.post(
                f"http://{host}:{DEFAULT_MOONRAKER_PORT}/printer/objects/query",
                json={"objects": {"print_stats": None}},
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_HTTP_TIMEOUT_S
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("result", {}).get("status", {}).get("print_stats", {}).get("state", "Недоступен")
            self.logger.debug(f"Printer info for {host}: hostname={hostname}, state={state}")
        except requests.RequestException as e:
            self.logger.debug(f"Failed to get printer info for {host}: {e}")

        self.printer_info_cache[host] = (hostname, state)
        return hostname, state

    def check_network_connectivity(self):
        """Проверяет доступность сети."""
        try:
            socket.gethostbyname("google.com")
            self.logger.debug("Network connectivity test passed")
            return True
        except Exception as e:
            self.logger.error(f"Network connectivity test failed: {e}")
            return False

    def send_printer_command(self, host, command):
        """Отправляет команду Moonraker API для управления печатью.

        Возвращает кортеж (success: bool, status_code: int | None).
        Бросает requests.RequestException при сетевых ошибках.
        """
        commands = {
            "start": "/printer/print/start",
            "pause": "/printer/print/pause",
            "cancel": "/printer/print/cancel",
            "emergency_stop": "/printer/emergency_stop"
        }
        if command not in commands:
            self.logger.error(f"Unknown command: {command}")
            return False, None
        url = f"http://{host}:{DEFAULT_MOONRAKER_PORT}{commands[command]}"
        try:
            response = requests.post(url, timeout=5)
            self.logger.debug(f"Sent command {command} to {host}, status={response.status_code}")
            return response.status_code == 200, response.status_code
        except requests.RequestException as e:
            self.logger.error(f"Failed to send {command} command to {host}: {e}")
            raise
