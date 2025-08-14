import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QProgressBar, QCheckBox, QMenu, \
    QSpacerItem, QSizePolicy, QMessageBox, QInputDialog, QApplication, QSystemTrayIcon, QTableWidgetItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import os
import platform
from config import ConfigManager
from scanner import ScanThread
from network import NetworkUtils
from utils import APP_NAME, open_ssh_terminal, LOG_LEVELS, set_log_level
from HostTable import HostTable
from WebcamDialog import WebcamDialog
from SettingsDialog import SettingsDialog
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 800, 600)
        self.logger = logging.getLogger(__name__)

        QApplication.setQuitOnLastWindowClosed(False)

        self.config_manager = ConfigManager()
        self.network_utils = NetworkUtils()
        self.config = self.config_manager.load_config()
        self.subnets = self.config.get("subnets", [])
        self.known_hosts = self.config.get("hosts", {})
        self.notification_states = self.config.get("notification_states", [])
        self.ssh_user = self.config.get("ssh_user", "")
        self.log_level = self.config.get("log_level", "INFO")
        self.auto_refresh = self.config.get("auto_refresh", True)
        self.previous_states = {}
        self.current_hosts = []
        self.config_file_opened = False

        set_log_level(self.log_level)

        if not self.subnets:
            self.subnets = [self.network_utils.get_local_subnet()]
            self.config_manager.save_current_config(self)

        icon_path = ""
        if platform.system() == "Windows":
            icon_path = resource_path("icon.ico")
        elif platform.system() == "Darwin":
            icon_path = resource_path("icon.icns")
        else:
            icon_path = resource_path("icon.png")

        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray is not available on this system")
        tray_menu = QMenu()
        tray_menu.addAction("Показать", self.show)
        tray_menu.addAction("Закрыть", QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setVisible(True)
        self.logger.debug("System tray icon initialized")
        self.check_notification_permissions()

        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        button_layout = QHBoxLayout()
        buttons = [
            ("Настройки", self.open_settings),
            ("Сканировать", self.scan_network),
            ("Обновить", self.refresh_hosts)
        ]
        self.scan_button = None
        self.refresh_button = None
        for text, slot in buttons:
            button = QPushButton(text)
            button.clicked.connect(slot)
            button_layout.addWidget(button)
            if text == "Сканировать":
                self.scan_button = button
            elif text == "Обновить":
                self.refresh_button = button
        self.auto_refresh_checkbox = QCheckBox("Автообновление")
        self.auto_refresh_checkbox.setChecked(self.auto_refresh)
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_checkbox)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.table = HostTable(self)
        self.table.cellClicked.connect(self.cell_clicked)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        exit_layout = QHBoxLayout()
        exit_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.exit_button = QPushButton("Свернуть в трей")
        self.exit_button.setFixedWidth(140)
        self.exit_button.clicked.connect(self.hide_to_tray)
        exit_layout.addWidget(self.exit_button)
        self.close_button = QPushButton("Закрыть")
        self.close_button.setFixedWidth(140)
        self.close_button.clicked.connect(self.close)
        exit_layout.addWidget(self.close_button)
        layout.addLayout(exit_layout)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(lambda: self.refresh_hosts(auto=True))
        if self.auto_refresh:
            self.refresh_timer.start(1000)

        self.initialize_table()

    def toggle_auto_refresh(self, state):
        self.auto_refresh = state == Qt.CheckState.Checked.value
        if self.auto_refresh:
            self.refresh_timer.start(300)
        else:
            self.refresh_timer.stop()
        self.config_manager.save_current_config(self)
        self.logger.debug(f"Auto-refresh set to {self.auto_refresh}")

    def open_settings(self):
        dialog = SettingsDialog(self.subnets, self.notification_states, self.ssh_user, self.log_level,
                               self.config_manager, self)
        self.config_file_opened = True
        if dialog.exec():
            self.subnets = dialog.get_subnets()
            self.notification_states = dialog.get_notification_states()
            self.ssh_user = dialog.get_ssh_credentials()
            self.log_level = dialog.get_log_level()
            self.config_file_opened = False
            self.config_manager.save_current_config(self)
            self.logger.debug(
                f"Settings updated: subnets={self.subnets}, notification_states={self.notification_states}, "
                f"ssh_user={self.ssh_user}, log_level={self.log_level}")

    def check_notification_permissions(self):
        try:
            self.tray_icon.showMessage(
                APP_NAME,
                "Убедитесь, что уведомления разрешены в Системных настройках > Уведомления > Moonraker Host Scanner",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )
            self.logger.debug("Checking notification permissions")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def hide_to_tray(self):
        self.hide()
        try:
            self.tray_icon.showMessage(
                APP_NAME,
                "Программа свернута в трей. Кликните правой кнопкой для действий.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self.logger.debug("Application minimized to system tray")
        except Exception as e:
            self.logger.error(f"Failed to send tray notification: {e}")

    def show_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid() or index.column() != 0:
            return
        menu = QMenu()
        rename_action = menu.addAction("Переименовать")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == rename_action:
            row = index.row()
            host = self.table.item(row, 1).text().lstrip('🟢🔴 ').strip()
            current_name = self.table.item(row, 0).text().lstrip('▶▼ ').strip()
            new_name, ok = QInputDialog.getText(self, "Переименовать хост", "Введите новое имя:", text=current_name)
            if ok and new_name:
                self.known_hosts[host]["custom_name"] = new_name
                self.config_manager.save_current_config(self)
                triangle = "▼" if host in self.table.expanded_rows else "▶"
                self.table.setItem(row, 0, QTableWidgetItem(f"{triangle} {new_name}"))
                if host not in self.current_hosts:
                    self.current_hosts.append(host)
                self.logger.debug(f"Renamed host {host} to {new_name}, current_hosts: {self.current_hosts}")

    def cell_clicked(self, row, column):
        if column == 5:  # Игнорируем клики по столбцу с кнопками
            return
        host = self.table.item(row, 1).text().lstrip('🟢🔴 ').strip()
        if column == 0:  # Клик по имени
            self.table.toggle_control_row(row, host)
        elif column == 1:  # Хост
            import webbrowser
            webbrowser.open(f"http://{host}")
            self.logger.debug(f"Opened browser for host: {host}")
        elif column == 2:  # SSH
            try:
                open_ssh_terminal(host, self.ssh_user)
                self.logger.debug(f"Attempted SSH connection for host: {host}")
            except RuntimeError as e:
                self.logger.error(f"SSH connection failed for {host}: {e}")
                QMessageBox.critical(self, "Ошибка SSH", f"Не удалось подключиться к {host}: {str(e)}")
        elif column == 4:  # Камера
            dialog = WebcamDialog(host, self)
            dialog.exec()
            self.logger.debug(f"Opened webcam dialog for host: {host}")

    def delete_host(self, host, row):
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить хост {host}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if host in self.known_hosts:
                del self.known_hosts[host]
            if host in self.current_hosts:
                self.current_hosts.remove(host)
            # Удаляем строку управления, если она открыта
            if host in self.table.expanded_rows:
                self.table.removeRow(self.table.expanded_rows[host])
                del self.table.expanded_rows[host]
            self.table.removeRow(row)
            self.config_manager.save_current_config(self)
            self.logger.debug(f"Deleted host {host} from configuration and table")

    def update_progress(self, value):
        self.progress_bar.setValue(int(value))
        self.logger.debug(f"Progress updated: {value}%")

    def initialize_table(self):
        self.table.setRowCount(0)
        self.current_hosts = []
        for host, host_info in self.known_hosts.items():
            hostname, state = self.network_utils.get_printer_info(host)
            self.known_hosts[host]["original_name"] = hostname or "Неизвестно"
            display_name = host_info.get("custom_name") if host_info.get("custom_name") is not None else (hostname or "Неизвестно")
            self.current_hosts.append(host)
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.add_host(row, host, display_name, "Оффлайн", self.known_hosts)
            self.logger.debug(f"Initialized host {host} with display_name={display_name}")

    def add_host_to_table(self, host, hostname, state):
        hostname = hostname or "Неизвестно"
        if host not in self.known_hosts:
            self.known_hosts[host] = {"original_name": hostname, "custom_name": None}
            self.logger.debug(f"Added new host {host} with original_name={hostname}")
        else:
            self.known_hosts[host]["original_name"] = hostname
            self.logger.debug(f"Updated original_name for {host} to {hostname}")
        custom_name = self.known_hosts[host].get("custom_name") if self.known_hosts[host].get("custom_name") is not None else hostname
        was_updated = self.table.update_host_state(host, custom_name, state, self.known_hosts)
        if not was_updated:
            self.current_hosts.append(host)
        if state in self.notification_states and (
                host not in self.previous_states or self.previous_states[host] != state):
            try:
                self.tray_icon.showMessage(
                    APP_NAME,
                    f"{custom_name} ({host}) получил статус {state}",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )
                self.logger.debug(f"Notification sent for {host}: {custom_name} ({host}) получил статус {state}")
            except Exception as e:
                self.logger.error(f"Failed to send notification for {host}: {e}")
        self.previous_states[host] = state

    def handle_thread_error(self, message, auto=False):
        QMessageBox.critical(self, "Ошибка", message)
        self.progress_bar.setVisible(False)
        if not auto:
            self.scan_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
        self.logger.debug(f"Error shown: {message}")

    def scan_network(self):
        self.scan_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.scan_thread = ScanThread(self.subnets, self.known_hosts.keys(), self.network_utils)
        self.scan_thread.host_found.connect(self.add_host_to_table)
        self.scan_thread.progress_updated.connect(self.update_progress)
        self.scan_thread.error_occurred.connect(lambda message: self.handle_thread_error(message, auto=False))
        self.scan_thread.scan_finished.connect(lambda hosts: self.finish_scan(hosts, auto=False))
        self.scan_thread.start()
        self.logger.debug("Started network scan")

    def refresh_hosts(self, auto=False):
        if not auto:
            self.scan_button.setEnabled(False)
            self.refresh_button.setEnabled(True)
        self.scan_thread = ScanThread([], self.known_hosts.keys(), self.network_utils)
        self.scan_thread.host_found.connect(self.add_host_to_table)
        self.scan_thread.progress_updated.connect(self.update_progress)
        self.scan_thread.error_occurred.connect(lambda message: self.handle_thread_error(message, auto))
        self.scan_thread.scan_finished.connect(lambda hosts: self.finish_scan(hosts, auto))
        self.scan_thread.start()
        self.logger.debug(f"Started refresh hosts (auto={auto})")

    def finish_scan(self, hosts, auto):
        new_hosts = {}
        for host in hosts:
            hostname, _ = self.network_utils.get_printer_info(host)
            hostname = hostname or "Неизвестно"
            new_hosts[host] = {
                "original_name": hostname,
                "custom_name": self.known_hosts.get(host, {}).get("custom_name", None)
            }
            self.logger.debug(f"Scanned host {host} with original_name={hostname}")
        for host in self.known_hosts:
            if host not in new_hosts:
                new_hosts[host] = self.known_hosts[host]
        self.known_hosts = new_hosts
        self.config_manager.save_current_config(self)
        self.progress_bar.setVisible(False)
        if not auto:
            self.scan_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
        self.logger.debug(f"Scan finished, updated hosts: {new_hosts}")

    def show_error(self, message, auto):
        self.handle_thread_error(message, auto)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Подтверждение выхода",
            "Вы действительно хотите выйти из приложения?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_file_opened = False
            QApplication.quit()
        else:
            event.ignore()