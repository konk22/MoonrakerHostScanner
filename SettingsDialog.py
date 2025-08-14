import ipaddress
import json
import logging
import os

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QPushButton, QListWidget, QInputDialog, QMessageBox, QCheckBox, QLineEdit, QLabel, QComboBox, QTextEdit, QHBoxLayout

class SettingsDialog(QDialog):
    """Модальное окно настроек с вкладками."""
    def __init__(self, subnets, notification_states, ssh_user, log_level, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        # Устанавливаем размер окна таким же, как у MainWindow
        if parent:
            self.resize(parent.size())
        else:
            self.setGeometry(100, 100, 800, 600)  # Запасной размер, если parent отсутствует
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

        # Вкладка "SSH"
        self.ssh_tab = QWidget()
        self.setup_ssh_tab()
        self.tabs.addTab(self.ssh_tab, "SSH")

        # Вкладка "Конфигурация"
        self.config_tab = QWidget()
        self.setup_config_tab()
        self.tabs.addTab(self.config_tab, "Конфигурация")

        # Вкладка "Логи"
        self.logs_tab = QWidget()
        self.setup_logs_tab()
        self.tabs.addTab(self.logs_tab, "Логи")

        # Вкладка "About"
        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, "About")

        layout.addWidget(self.tabs)
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        # Подключаем сигнал смены вкладки для обновления текста кнопки
        self.tabs.currentChanged.connect(self.update_save_button_text)

    def update_save_button_text(self, index):
        """Обновляет текст кнопки 'Сохранить' в зависимости от активной вкладки."""
        if index in [3, 4, 5]:  # Индексы вкладок "Логи" (3) и "Конфигурация" (4)
            self.save_button.setText("Закрыть")
        else:
            self.save_button.setText("Сохранить")
        self.logger.debug(f"Updated save button text to '{self.save_button.text()}' for tab index {index}")

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
        log_file = os.path.join(self.config_manager.config_dir, "moonraker_scanner.log")
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                self.logs_text.setText(f.read())
        except FileNotFoundError:
            self.logs_text.setText("Файл логов не найден.")
        layout.addWidget(self.logs_text)
        self.logs_tab.setLayout(layout)

    def setup_config_tab(self):
        """Настраивает вкладку для редактирования config.json."""
        layout = QVBoxLayout()
        self.config_editor = QTextEdit()
        self.config_editor.setFontFamily("Courier")  # Моноширинный шрифт для JSON
        try:
            with open(self.config_manager.config_file, "r", encoding="utf-8") as f:
                self.config_editor.setText(f.read())
        except FileNotFoundError:
            self.config_editor.setText(json.dumps({}, indent=4, ensure_ascii=False))
        layout.addWidget(self.config_editor)

        button_layout = QHBoxLayout()
        clear_button = QPushButton("Очистить конфигурацию")
        clear_button.clicked.connect(self.clear_config)
        button_layout.addWidget(clear_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_config_editor)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.cancel_config_editor)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.config_tab.setLayout(layout)

    def save_config_editor(self):
        """Сохраняет изменения из редактора конфигурации."""
        try:
            config_text = self.config_editor.toPlainText()
            # Проверяем валидность JSON
            config = json.loads(config_text)
            # Сохраняем конфигурацию
            with open(self.config_manager.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.logger.debug("Config editor changes saved")
            # Обновляем данные в MainWindow
            parent = self.parent()
            parent.config = config
            parent.subnets = config.get("subnets", [parent.network_utils.get_local_subnet()])
            parent.known_hosts = config.get("hosts", {})
            parent.notification_states = config.get("notification_states", [])
            parent.ssh_user = config.get("ssh_user", "")
            parent.log_level = config.get("log_level", "INFO")
            parent.auto_refresh = config.get("auto_refresh", True)
            parent.current_hosts = list(parent.known_hosts.keys())
            parent.table.setRowCount(0)
            parent.initialize_table()
            # Редактор конфигурации закрыт: синхронизация состояний выполнена
            QMessageBox.information(self, "Успех", "Конфигурация сохранена.")
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON format in config editor")
            QMessageBox.critical(self, "Ошибка", "Некорректный формат JSON.")
        except Exception as e:
            self.logger.error(f"Failed to save config from editor: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить конфигурацию: {str(e)}")

    def cancel_config_editor(self):
        """Отменяет изменения в редакторе конфигурации."""
        try:
            with open(self.config_manager.config_file, "r", encoding="utf-8") as f:
                self.config_editor.setText(f.read())
        except FileNotFoundError:
            self.config_editor.setText(json.dumps({}, indent=4, ensure_ascii=False))
        # Отмена изменений редактора: откат к состоянию на диске выполнен
        self.logger.debug("Config editor changes cancelled")

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
            # Очищаем файл конфигурации
            self.config_manager.clear_config()
            # Сбрасываем данные в MainWindow
            parent = self.parent()
            parent.subnets = [parent.network_utils.get_local_subnet()]
            parent.known_hosts = {}
            parent.notification_states = []
            parent.ssh_user = ""
            parent.log_level = "INFO"
            parent.current_hosts = []
            parent.previous_states = {}
            # Обновляем UI
            self.subnet_list.clear()
            self.subnet_list.addItems(parent.subnets)
            for state, checkbox in self.checkboxes.items():
                checkbox.setChecked(False)
            self.ssh_user_input.setText("")
            self.log_level_combo.setCurrentText("INFO")
            parent.table.setRowCount(0)  # Очищаем таблицу
            self.config_editor.setText(json.dumps({}, indent=4, ensure_ascii=False))  # Очищаем редактор
            QMessageBox.information(self, "Успех", "Конфигурация очищена.")
            self.logger.debug("Configuration cleared and UI updated")

    def get_subnets(self):
        return self.subnets

    def get_notification_states(self):
        return [state for state, checkbox in self.checkboxes.items() if checkbox.isChecked()]

    def get_ssh_credentials(self):
        return self.ssh_user_input.text()

    def get_log_level(self):
        return self.log_level_combo.currentText()