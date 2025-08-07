import sys
import json
import socket
import ipaddress
import webbrowser
import os
import requests
import subprocess
from appdirs import user_config_dir
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QDialog, QListWidget,
                             QInputDialog, QMessageBox, QHeaderView, QProgressBar, QMenu)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

CONFIG_DIR = user_config_dir("MoonrakerScanner", "xAI")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def ensure_config_dir():
    """Создает директорию конфигурации, если она не существует."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def load_config():
    """Загружает конфигурацию из JSON-файла."""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"subnets": [], "hosts": {}}

def save_config(subnets, hosts):
    """Сохраняет конфигурацию в JSON-файл."""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"subnets": subnets, "hosts": hosts}, f, indent=4)

def clear_config():
    """Очищает файл конфигурации."""
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

def open_config_file():
    """Открывает config.json в системном текстовом редакторе."""
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        if sys.platform == "win32":
            os.startfile(CONFIG_FILE)
        else:
            subprocess.run(["open", CONFIG_FILE], check=True)
    else:
        QMessageBox.warning(None, "Ошибка", "Файл config.json не существует.")

def get_local_subnet():
    """Получает подсеть локального компьютера."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        return str(ipaddress.ip_network(f"{ip}/24", strict=False))
    finally:
        s.close()

def scan_port(ip, port=7125, timeout=1):
    """Проверяет, открыт ли порт на указанном IP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((str(ip), port))
            return str(ip) if result == 0 else None
    except:
        return None

def get_printer_info(host):
    """Получает hostname и state принтера через API Moonraker."""
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
    except requests.RequestException:
        pass
    return hostname, state

def scan_network(subnets, known_hosts=None, progress_callback=None):
    """Сканирует подсети и известные хосты на наличие порта 7125."""
    open_hosts = set()
    known_hosts = set(known_hosts or [])
    total_hosts = len(known_hosts) + sum(len(list(ipaddress.ip_network(subnet, strict=False).hosts())) for subnet in subnets)
    scanned_hosts = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scan_port, ip) for ip in known_hosts]
        for future in futures:
            scanned_hosts += 1
            result = future.result()
            if result:
                open_hosts.add(result)
            if progress_callback:
                progress_callback(scanned_hosts / total_hosts * 100)

    for subnet in subnets:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(scan_port, ip) for ip in network.hosts()]
                for future in futures:
                    scanned_hosts += 1
                    result = future.result()
                    if result:
                        open_hosts.add(result)
                    if progress_callback:
                        progress_callback(scanned_hosts / total_hosts * 100)
        except ValueError:
            continue

    return list(open_hosts)

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

class SubnetDialog(QDialog):
    """Диалог для управления подсетями."""
    def __init__(self, subnets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление подсетями")
        self.setGeometry(100, 100, 300, 400)
        self.subnets = subnets.copy()
        layout = QVBoxLayout()

        self.subnet_list = QListWidget()
        self.subnet_list.addItems(self.subnets)
        layout.addWidget(self.subnet_list)

        add_button = QPushButton("Добавить подсеть")
        add_button.clicked.connect(self.add_subnet)
        layout.addWidget(add_button)

        edit_button = QPushButton("Изменить подсеть")
        edit_button.clicked.connect(self.edit_subnet)
        layout.addWidget(edit_button)

        remove_button = QPushButton("Удалить подсеть")
        remove_button.clicked.connect(self.remove_subnet)
        layout.addWidget(remove_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def add_subnet(self):
        subnet, ok = QInputDialog.getText(self, "Добавить подсеть", "Введите подсеть (например, 192.168.1.0/24):")
        if ok and subnet and subnet not in self.subnets:
            try:
                ipaddress.ip_network(subnet, strict=False)
                self.subnets.append(subnet)
                self.subnet_list.clear()
                self.subnet_list.addItems(self.subnets)
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Некорректный формат подсети!")

    def edit_subnet(self):
        current = self.subnet_list.currentItem()
        if current:
            subnet, ok = QInputDialog.getText(self, "Изменить подсеть", "Введите новую подсеть:", text=current.text())
            if ok and subnet:
                try:
                    ipaddress.ip_network(subnet, strict=False)
                    index = self.subnets.index(current.text())
                    self.subnets[index] = subnet
                    self.subnet_list.clear()
                    self.subnet_list.addItems(self.subnets)
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", "Некорректный формат подсети!")

    def remove_subnet(self):
        current = self.subnet_list.currentItem()
        if current:
            self.subnets.remove(current.text())
            self.subnet_list.clear()
            self.subnet_list.addItems(self.subnets)

    def get_subnets(self):
        return self.subnets

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moonraker Host Scanner")
        self.setGeometry(100, 100, 800, 600)

        # Загружаем конфигурацию
        self.config = load_config()
        self.subnets = self.config.get("subnets", [])
        self.known_hosts = self.config.get("hosts", {})

        # Если подсетей нет, добавляем локальную подсеть
        if not self.subnets:
            self.subnets = [get_local_subnet()]
            save_config(self.subnets, self.known_hosts)

        # Основной виджет и layout
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # Кнопки управления
        button_layout = QHBoxLayout()
        manage_button = QPushButton("Управление подсетями")
        manage_button.clicked.connect(self.manage_subnets)
        button_layout.addWidget(manage_button)

        self.scan_button = QPushButton("Сканировать")
        self.scan_button.clicked.connect(self.scan_network)
        button_layout.addWidget(self.scan_button)

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.refresh_hosts)
        button_layout.addWidget(self.refresh_button)

        clear_config_button = QPushButton("Очистить конфигурацию")
        clear_config_button.clicked.connect(self.clear_config)
        button_layout.addWidget(clear_config_button)

        open_config_button = QPushButton("Открыть config.json")
        open_config_button.clicked.connect(open_config_file)
        button_layout.addWidget(open_config_button)
        layout.addLayout(button_layout)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Таблица для отображения хостов
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "№", "Имя", "Хост", "Статус", "Камера", "Резерв 3"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self.cell_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # Кнопка выхода
        exit_button = QPushButton("Выход")
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

        # Проверяем известные хосты при запуске
        self.refresh_hosts()

    def show_context_menu(self, position):
        """Показывает контекстное меню для переименования хоста."""
        index = self.table.indexAt(position)
        if not index.isValid() or index.column() != 1:  # Только для столбца "Имя"
            return

        menu = QMenu()
        rename_action = menu.addAction("Переименовать")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == rename_action:
            row = index.row()
            host = self.table.item(row, 2).text()  # IP из столбца "Хост"
            current_name = self.table.item(row, 1).text()
            new_name, ok = QInputDialog.getText(self, "Переименовать хост", "Введите новое имя:", text=current_name)
            if ok and new_name:
                self.known_hosts[host] = new_name
                save_config(self.subnets, self.known_hosts)
                self.refresh_hosts()

    def cell_clicked(self, row, column):
        """Обрабатывает клик по ячейкам таблицы."""
        if column == 2:  # Столбец "Хост"
            host = self.table.item(row, column).text()
            webbrowser.open(f"http://{host}:7125")
        elif column == 4:  # Столбец "Камера"
            host = self.table.item(row, 2).text()
            dialog = WebcamDialog(host, self)
            dialog.exec()

    def update_progress(self, value):
        """Обновляет прогресс-бар."""
        self.progress_bar.setValue(int(value))
        QApplication.processEvents()

    def clear_config(self):
        """Очищает конфигурацию после подтверждения."""
        reply = QMessageBox.question(
            self, "Подтверждение", "Вы уверены, что хотите очистить конфигурацию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_config()
            self.subnets = [get_local_subnet()]
            self.known_hosts = {}
            save_config(self.subnets, self.known_hosts)
            self.table.setRowCount(0)
            QMessageBox.information(self, "Успех", "Конфигурация очищена.")

    def refresh_hosts(self):
        """Проверяет доступность известных хостов."""
        if not self.known_hosts:
            self.table.setRowCount(0)
            return

        self.scan_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.table.setRowCount(len(self.known_hosts))

        def progress_callback(value):
            self.update_progress(value)

        hosts = scan_network([], self.known_hosts.keys(), progress_callback)
        # Сохраняем кастомные имена для существующих хостов
        new_hosts = {host: self.known_hosts.get(host, "Неизвестно") for host in hosts}
        self.known_hosts = new_hosts
        save_config(self.subnets, self.known_hosts)

        self.table.setRowCount(len(hosts))
        for i, host in enumerate(hosts):
            hostname, state = get_printer_info(host)
            custom_name = self.known_hosts.get(host, hostname)
            items = [
                QTableWidgetItem(str(i + 1)),
                QTableWidgetItem(custom_name),
                QTableWidgetItem(host),
                QTableWidgetItem(state),
                QTableWidgetItem("Открыть"),
                QTableWidgetItem("")
            ]
            for item in items:
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for j, item in enumerate(items):
                self.table.setItem(i, j, item)

        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def scan_network(self):
        """Сканирует сеть и обновляет таблицу."""
        self.scan_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.table.setRowCount(0)

        def progress_callback(value):
            self.update_progress(value)

        hosts = scan_network(self.subnets, self.known_hosts.keys(), progress_callback)
        # Сохраняем кастомные имена для существующих хостов
        new_hosts = {host: self.known_hosts.get(host, get_printer_info(host)[0]) for host in hosts}
        self.known_hosts = new_hosts
        save_config(self.subnets, self.known_hosts)

        self.table.setRowCount(len(hosts))
        for i, host in enumerate(hosts):
            hostname, state = get_printer_info(host)
            custom_name = self.known_hosts.get(host, hostname)
            items = [
                QTableWidgetItem(str(i + 1)),
                QTableWidgetItem(custom_name),
                QTableWidgetItem(host),
                QTableWidgetItem(state),
                QTableWidgetItem("Открыть"),
                QTableWidgetItem("")
            ]
            for item in items:
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for j, item in enumerate(items):
                self.table.setItem(i, j, item)

        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def manage_subnets(self):
        """Открывает диалог управления подсетями."""
        dialog = SubnetDialog(self.subnets, self)
        if dialog.exec():
            self.subnets = dialog.get_subnets()
            save_config(self.subnets, self.known_hosts)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())