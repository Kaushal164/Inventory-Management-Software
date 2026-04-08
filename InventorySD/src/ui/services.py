from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db import exec1, q, utc_now_iso
from src.ui.widgets import money_edit, warn


class ServicesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.selected_id: int | None = None
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search by code or name…")
        self.query.textChanged.connect(lambda _t: self.refresh())

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Code", "Name", "Price"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.code = QLineEdit()
        self.name = QLineEdit()
        self.price = money_edit()

        form = QFormLayout()
        form.addRow("Code", self.code)
        form.addRow("Name*", self.name)
        form.addRow("Price", self.price)

        box = QGroupBox("Service")
        box.setLayout(form)

        btn_new = QPushButton("New")
        btn_save = QPushButton("Save")
        btn_delete = QPushButton("Delete")
        btn_refresh = QPushButton("Refresh")
        btn_save.setObjectName("primaryButton")
        btn_delete.setObjectName("dangerButton")
        btn_new.clicked.connect(self._new)
        btn_save.clicked.connect(self._save)
        btn_delete.clicked.connect(self._delete)
        btn_refresh.clicked.connect(self.refresh)

        btns = QHBoxLayout()
        btns.addWidget(btn_new)
        btns.addWidget(btn_save)
        btns.addWidget(btn_delete)
        btns.addStretch(1)
        btns.addWidget(btn_refresh)

        root = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(QLabel("Services"))
        top.addStretch(1)
        top.addWidget(self.query)
        root.addLayout(top)
        root.addWidget(self.table, 1)
        root.addWidget(box)
        root.addLayout(btns)
        self.setLayout(root)

        self.refresh()

    def refresh(self) -> None:
        needle = self.query.text().strip()
        rows = q(
            self.conn,
            "SELECT id, code, name, price "
            "FROM services "
            "WHERE (? = '' OR COALESCE(code,'') LIKE '%'||?||'%' OR name LIKE '%'||?||'%') "
            "ORDER BY id DESC",
            (needle, needle, needle),
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [row["id"], row["code"] or "", row["name"], f'{float(row["price"]):.2f}']
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.table.resizeColumnsToContents()
        self._new()

    def _new(self) -> None:
        self.selected_id = None
        self.code.setText("")
        self.name.setText("")
        self.price.setText("0.00")
        self.table.clearSelection()

    def _on_select(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        rid = int(self.table.item(items[0].row(), 0).text())
        row = self.conn.execute(
            "SELECT id, code, name, price FROM services WHERE id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            return
        self.selected_id = int(row["id"])
        self.code.setText(row["code"] or "")
        self.name.setText(row["name"])
        self.price.setText(f'{float(row["price"]):.2f}')

    def _save(self) -> None:
        name = self.name.text().strip()
        if not name:
            warn(self, "Validation", "Name is required.")
            return
        code = self.code.text().strip() or None
        price = float(self.price.text() or 0)

        if self.selected_id is None:
            exec1(
                self.conn,
                "INSERT INTO services (code, name, price, created_at) VALUES (?,?,?,?)",
                (code, name, price, utc_now_iso()),
            )
        else:
            self.conn.execute(
                "UPDATE services SET code=?, name=?, price=? WHERE id=?",
                (code, name, price, self.selected_id),
            )
            self.conn.commit()
        self.refresh()

    def _delete(self) -> None:
        if self.selected_id is None:
            return
        from PyQt6.QtWidgets import QMessageBox

        if (
            QMessageBox.question(
                self,
                "Delete service",
                "Delete the selected service? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.conn.execute("DELETE FROM services WHERE id = ?", (self.selected_id,))
        self.conn.commit()
        self.refresh()

