# network.py

import socket
import ipaddress
import requests
import logging
from cachetools import TTLCache


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

    def scan_port(self, ip, port=7125, timeout=1):
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
            response = requests.get(f"http://{host}:7125/printer/info", timeout=2)
            if response.status_code == 200:
                data = response.json()
                hostname = data.get("result", {}).get("hostname", "Неизвестно")

            response = requests.post(
                f"http://{host}:7125/printer/objects/query",
                json={"objects": {"print_stats": None}},
                headers={"Content-Type": "application/json"},
                timeout=2
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
