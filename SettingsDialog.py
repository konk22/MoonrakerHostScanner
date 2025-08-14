# SettingDialog.py

import ipaddress
import logging
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QPushButton, QListWidget, QInputDialog, \
    QMessageBox, QCheckBox, QLineEdit, QLabel, QComboBox, QTextEdit


class SettingsDialog(QDialog):
    """Модальное окно настроек с вкладками."""

    def __init__(self, subnets, notification_states, ssh_user, log_level, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setGeometry(100, 100, 400, 400)
        self.setModal(True)
        self.subnets = subnets.copy()
        self.notification_states = notification_states.copy()
        self.ssh_user = ssh_user
        self.log_level = log_level
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Вкладка "Управление подсетями"
        self.subnet_tab = QWidget()
        self.setup_subnet_tab()
        self.tabs.addTab(self.subnet_tab, "Управление подсетями")

        # Вкладка "Оповещения"
        self.notification_tab = QWidget()
        self.setup_notification_tab()
        self.tabs.addTab(self.notification_tab, "Оповещения")

        # Вкладка "Конфигурация"
        self.config_tab = QWidget()
        self.setup_config_tab()
        self.tabs.addTab(self.config_tab, "Конфигурация")

        # Вкладка "SSH"
        self.ssh_tab = QWidget()
        self.setup_ssh_tab()
        self.tabs.addTab(self.ssh_tab, "SSH")

        # Вкладка "Логи"
        self.logs_tab = QWidget()
        self.setup_logs_tab()
        self.tabs.addTab(self.logs_tab, "Логи")

        # Вкладка "About"
        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, "About")

        layout.addWidget(self.tabs)
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def setup_subnet_tab(self):
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

        self.subnet_tab.setLayout(layout)

    def add_subnet(self):
        subnet, ok = QInputDialog.getText(self, "Добавить подсеть", "Введите подсеть (например, 192.168.1.0/24):")
        if ok and subnet and subnet not in self.subnets:
            try:
                ipaddress.ip_network(subnet, strict=False)
                self.subnets.append(subnet)
                self.subnet_list.addItem(subnet)
                self.logger.debug(f"Added subnet: {subnet}")
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
                    current.setText(subnet)
                    self.logger.debug(f"Edited subnet: {subnet}")
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", "Некорректный формат подсети!")

    def remove_subnet(self):
        current = self.subnet_list.currentItem()
        if current:
            subnet = current.text()
            try:
                self.subnets.remove(subnet)
                self.subnet_list.takeItem(self.subnet_list.row(current))
                self.logger.debug(f"Removed subnet: {subnet}")
            except ValueError:
                self.logger.error(f"Failed to remove subnet: {subnet} not found in self.subnets")
                QMessageBox.warning(self, "Ошибка", f"Подсеть {subnet} не найдена в списке.")
        else:
            self.logger.warning("No subnet selected for removal")
            QMessageBox.warning(self, "Ошибка", "Выберите подсеть для удаления.")

    def setup_notification_tab(self):
        layout = QVBoxLayout()
        self.checkboxes = {}
        states = ["printing", "paused", "error", "ready", "standby", "Оффлайн"]
        for state in states:
            checkbox = QCheckBox(state.capitalize())
            checkbox.setChecked(state in self.notification_states)
            self.checkboxes[state] = checkbox
            layout.addWidget(checkbox)
        self.notification_tab.setLayout(layout)

    def setup_config_tab(self):
        layout = QVBoxLayout()
        clear_button = QPushButton("Очистить конфигурацию")
        clear_button.clicked.connect(self.clear_config)
        layout.addWidget(clear_button)

        open_button = QPushButton("Открыть config.json")
        open_button.clicked.connect(self.config_manager.open_config_file)
        layout.addWidget(open_button)

        layout.addStretch()
        self.config_tab.setLayout(layout)

    def setup_ssh_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Имя пользователя для SSH (оставьте пустым для значения по умолчанию):"))
        self.ssh_user_input = QLineEdit(self.ssh_user or "")
        layout.addWidget(self.ssh_user_input)
        layout.addStretch()
        self.ssh_tab.setLayout(layout)

    def setup_logs_tab(self):
        layout = QVBoxLayout()
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText(self.log_level)
        self.log_level_combo.currentTextChanged.connect(self.update_log_level)
        layout.addWidget(QLabel("Уровень логирования:"))
        layout.addWidget(self.log_level_combo)
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        import os
        log_file = os.path.expanduser("~/.moonraker_scanner/moonraker_scanner.log")
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                self.logs_text.setText(f.read())
        except FileNotFoundError:
            self.logs_text.setText("Файл логов не найден.")
        layout.addWidget(self.logs_text)
        self.logs_tab.setLayout(layout)

    def update_log_level(self, level):
        from utils import set_log_level
        set_log_level(level)
        self.logger.debug(f"Log level changed to {level}")

    def setup_about_tab(self):
        layout = QVBoxLayout()
        self.about_text = QTextEdit()
        self.about_text.setReadOnly(True)
        try:
            with open("about.md", "r", encoding="utf-8") as f:
                self.about_text.setText(f.read())
        except FileNotFoundError:
            self.about_text.setText("Файл about.md не найден в корне проекта.")
        layout.addWidget(self.about_text)
        self.about_tab.setLayout(layout)

    def clear_config(self):
        reply = QMessageBox.question(
            self, "Подтверждение", "Вы уверены, что хотите очистить конфигурацию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.clear_config()
            self.subnets = [self.parent().network_utils.get_local_subnet()]
            self.notification_states = []
            self.ssh_user = ""
            self.log_level = "INFO"
            self.subnet_list.clear()
            self.subnet_list.addItems(self.subnets)
            for state, checkbox in self.checkboxes.items():
                checkbox.setChecked(False)
            self.ssh_user_input.setText("")
            self.log_level_combo.setCurrentText("INFO")
            QMessageBox.information(self, "Успех", "Конфигурация очищена.")
            self.logger.debug("Configuration cleared from settings dialog")

    def get_subnets(self):
        return self.subnets

    def get_notification_states(self):
        return [state for state, checkbox in self.checkboxes.items() if checkbox.isChecked()]

    def get_ssh_credentials(self):
        return self.ssh_user_input.text()

    def get_log_level(self):
        return self.log_level_combo.currentText()
