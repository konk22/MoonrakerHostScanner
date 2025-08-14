# HostTable.py

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt


class HostTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["Имя", "Хост", "SSH", "Статус", "Камера", "Резерв 3"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def add_host(self, row, host, hostname, state, known_hosts):
        """Добавляет хост в таблицу."""
        custom_name = known_hosts.get(host, hostname)
        items = [
            QTableWidgetItem(custom_name),
            QTableWidgetItem(host),
            QTableWidgetItem("Подключиться"),
            QTableWidgetItem(state),
            QTableWidgetItem("Открыть"),
            QTableWidgetItem("")
        ]
        for item in items:
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        for col in [1, 2, 4]:
            items[col].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        for j, item in enumerate(items):
            self.setItem(row, j, item)

    def update_host_state(self, host, hostname, state, known_hosts):
        """Обновляет состояние хоста в таблице или добавляет новый."""
        for row in range(self.rowCount()):
            if self.item(row, 1).text() == host:
                self.setItem(row, 0, QTableWidgetItem(known_hosts.get(host, hostname)))
                self.setItem(row, 3, QTableWidgetItem(state))
                return True
        row = self.rowCount()
        self.insertRow(row)
        self.add_host(row, host, hostname, state, known_hosts)
        return False
