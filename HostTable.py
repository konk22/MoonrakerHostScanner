from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
import logging


class HostTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["Имя", "Хост", "SSH", "Статус", "Камера", ""])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.parent = parent
        self.expanded_rows = {}  # Словарь для отслеживания открытых строк {host: row_index}
        self.logger = logging.getLogger(__name__)

        # Индексы колонок
        self.COL_NAME = 0
        self.COL_HOST = 1
        self.COL_SSH = 2
        self.COL_STATE = 3
        self.COL_CAMERA = 4
        self.COL_ACTIONS = 5

    def add_host(self, row, host, hostname, state, known_hosts):
        """Добавляет хост в таблицу."""
        host_info = known_hosts.get(host, {})
        custom_name = host_info.get("custom_name") if host_info.get("custom_name") is not None else hostname
        items = [
            QTableWidgetItem(f"▶ {custom_name}"),  # Добавляем треугольник
            QTableWidgetItem(f"{'🟢' if state != 'Оффлайн' else '🔴'} {host}"),
            QTableWidgetItem("Подключиться"),
            QTableWidgetItem(state),
            QTableWidgetItem("Открыть")
        ]
        for item in items:
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        for j, item in enumerate(items):
            self.setItem(row, j, item)

        items[self.COL_NAME].setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        items[self.COL_HOST].setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        delete_button = QPushButton("Удалить")
        delete_button.setFixedWidth(100)
        delete_button.setStyleSheet("background-color: #ff4d4d; color: white;")
        delete_button.clicked.connect(lambda: self.parent.delete_host(host, row))

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addStretch()
        layout.addWidget(delete_button)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setCellWidget(row, self.COL_ACTIONS, container)

    def update_host_state(self, host, hostname, state, known_hosts):
        """Обновляет состояние хоста в таблице или добавляет новый."""
        for row in range(self.rowCount()):
            if self.item(row, self.COL_HOST) and self.item(row, self.COL_HOST).text().lstrip('🟢🔴 ').strip() == host:
                host_info = known_hosts.get(host, {})
                custom_name = host_info.get("custom_name") if host_info.get("custom_name") is not None else hostname
                # Сохраняем состояние треугольника
                triangle = "▼" if host in self.expanded_rows else "▶"
                item_name = QTableWidgetItem(f"{triangle} {custom_name}")
                item_host = QTableWidgetItem(f"{'🟢' if state != 'Оффлайн' else '🔴'} {host}")
                item_state = QTableWidgetItem(state)
                item_state.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row, self.COL_NAME, item_name)
                self.setItem(row, self.COL_HOST, item_host)
                self.setItem(row, self.COL_STATE, item_state)
                delete_button = QPushButton("Удалить")
                delete_button.setFixedWidth(100)
                delete_button.setStyleSheet("background-color: #ff4d4d; color: white;")
                delete_button.clicked.connect(lambda: self.parent.delete_host(host, row))
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addStretch()
                layout.addWidget(delete_button)
                layout.addStretch()
                layout.setContentsMargins(0, 0, 0, 0)
                self.setCellWidget(row, self.COL_ACTIONS, container)
                return True
        row = self.rowCount()
        self.insertRow(row)
        self.add_host(row, host, hostname, state, known_hosts)
        return False

    def toggle_control_row(self, host):
        """Переключает отображение строки с кнопками управления."""
        main_row = self.find_host_row(host)
        if main_row is None:
            return

        if host in self.expanded_rows:
            # --- Скрываем строку ---
            control_row = self.expanded_rows.get(host, main_row + 1)
            if control_row < self.rowCount():
                self.removeRow(control_row)
            del self.expanded_rows[host]
            name_item = self.item(main_row, 0)  # Имя — теперь колонка 0
            if name_item:
                name_item.setText(f"▶ {name_item.text().lstrip('▼ ')}")
            self.logger.debug(f"Collapsed control row for host {host}")
        else:
            # --- Показываем строку ---
            control_row = main_row + 1
            self.insertRow(control_row)
            self.expanded_rows[host] = control_row  # Запоминаем индекс строки управления

            # Меняем треугольник на ▼
            name_item = self.item(main_row, 0)  # Имя — теперь колонка 0
            if name_item:
                name_item.setText(f"▼ {name_item.text().lstrip('▶ ')}")

            # Контейнер с кнопками
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            buttons = [
                ("Start", "start"),
                ("Pause", "pause"),
                ("Stop", "cancel"),
                ("Emergency Stop", "emergency_stop", "background-color: #ff4d4d; color: white;")
            ]
            for btn_text, cmd, *style in buttons:
                btn = QPushButton(btn_text)
                if style:
                    btn.setStyleSheet(style[0])
                btn.clicked.connect(lambda _, h=host, c=cmd: self.send_printer_command(h, c))
                layout.addWidget(btn)

            layout.addStretch()
            self.setCellWidget(control_row, self.COL_NAME, container)
            self.setSpan(control_row, self.COL_NAME, 1, self.columnCount())

            self.logger.debug(f"Expanded control row for host {host}")

    def find_host_row(self, host):
        """Возвращает индекс основной строки по хосту."""
        for r in range(self.rowCount()):
            if self.item(r, self.COL_HOST) and self.item(r, self.COL_HOST).text().lstrip('🟢🔴 ').strip() == host:
                return r
        return None

    def send_printer_command(self, host, command):
        """Отправляет команду Moonraker API через сетевой слой."""
        try:
            success, status_code = self.parent.network_utils.send_printer_command(host, command)
            if success:
                self.logger.debug(f"Successfully sent {command} command to {host}")
                hostname, state = self.parent.network_utils.get_printer_info(host)
                self.parent.add_host_to_table(host, hostname, state)
            else:
                status_text = status_code if status_code is not None else "unknown"
                self.logger.error(f"Failed to send {command} command to {host}: {status_text}")
                QMessageBox.critical(self.parent, "Ошибка",
                                     f"Не удалось выполнить команду {command}: {status_text}")
        except Exception as e:
            self.logger.error(f"Failed to send {command} command to {host}: {e}")
            QMessageBox.critical(self.parent, "Ошибка", f"{host}\nОшибка соединения при выполнении команды {command}: {str(e)}")