# scanner.py

from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import logging


class ScanThread(QThread):
    host_found = pyqtSignal(str, str, str)
    progress_updated = pyqtSignal(float)
    scan_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, subnets, known_hosts, network_utils):
        super().__init__()
        self.subnets = subnets
        self.known_hosts = known_hosts
        self.network_utils = network_utils
        self.logger = logging.getLogger(__name__)

    def run(self):
        open_hosts = set()
        known_hosts = set(self.known_hosts or [])
        total_hosts = len(known_hosts) + sum(
            len(list(ipaddress.ip_network(subnet, strict=False).hosts())) for subnet in self.subnets)
        scanned_hosts = 0
        self.logger.debug(
            f"Starting scan: {len(known_hosts)} known hosts, {len(self.subnets)} subnets, total={total_hosts}")

        if not self.network_utils.check_network_connectivity():
            self.error_occurred.emit("Нет доступа к сети. Проверьте подключение.")
            return

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.network_utils.scan_port, ip) for ip in known_hosts]
            for future in futures:
                scanned_hosts += 1
                result = future.result()
                if result:
                    open_hosts.add(result)
                    hostname, state = self.network_utils.get_printer_info(result)
                    self.host_found.emit(result, hostname, state)
                if total_hosts > 0:
                    self.progress_updated.emit(scanned_hosts / total_hosts * 100)

        for subnet in self.subnets:
            try:
                network = ipaddress.ip_network(subnet, strict=False)
                self.logger.debug(f"Scanning subnet: {subnet}")
                with ThreadPoolExecutor(max_workers=100) as executor:
                    futures = [executor.submit(self.network_utils.scan_port, ip) for ip in network.hosts()]
                    for future in futures:
                        scanned_hosts += 1
                        result = future.result()
                        if result:
                            open_hosts.add(result)
                            hostname, state = self.network_utils.get_printer_info(result)
                            self.host_found.emit(result, hostname, state)
                        if total_hosts > 0:
                            self.progress_updated.emit(scanned_hosts / total_hosts * 100)
            except ValueError as e:
                self.logger.error(f"Invalid subnet {subnet}: {e}")
                self.error_occurred.emit(f"Некорректная подсеть: {subnet}")
                continue

        for host in known_hosts - open_hosts:
            hostname, _ = self.network_utils.get_printer_info(host)
            self.host_found.emit(host, hostname, "Оффлайн")

        self.scan_finished.emit(list(open_hosts))
        self.logger.debug(f"Scan finished, found hosts: {open_hosts}")
