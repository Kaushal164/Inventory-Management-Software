from __future__ import annotations

import sqlite3

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db import exec1, q, sha256_hex, utc_now_iso
from src.ui.widgets import warn


class UsersPage(QWidget):
    def __init__(self, conn: sqlite3.Connection, current_user: dict):
        super().__init__()
        self.conn = conn
        self.current_user = current_user
        self.selected_id: int | None = None
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search by username…")
        self.query.textChanged.connect(lambda _t: self.refresh())

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Active", "Created At"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Set / reset password")
        self.role = QComboBox()
        self.role.addItems(["user", "admin"])
        self.active = QCheckBox("Active")
        self.active.setChecked(True)

        form = QFormLayout()
        form.addRow("Username*", self.username)
        form.addRow("Password", self.password)
        form.addRow("Role", self.role)
        form.addRow("", self.active)

        box = QGroupBox("User")
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
        top.addWidget(QLabel("Users"))
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
            "SELECT id, username, role, is_active, created_at "
            "FROM users "
            "WHERE (? = '' OR username LIKE '%'||?||'%') "
            "ORDER BY id DESC",
            (needle, needle),
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["id"],
                row["username"],
                row["role"],
                "Yes" if int(row["is_active"]) == 1 else "No",
                row["created_at"],
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.table.resizeColumnsToContents()
        self._new()

    def _new(self) -> None:
        self.selected_id = None
        self.username.setText("")
        self.password.setText("")
        self.role.setCurrentText("user")
        self.active.setChecked(True)
        self.table.clearSelection()

    def _on_select(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        rid = int(self.table.item(items[0].row(), 0).text())
        row = self.conn.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            return
        self.selected_id = int(row["id"])
        self.username.setText(row["username"])
        self.password.setText("")
        self.role.setCurrentText(row["role"])
        self.active.setChecked(int(row["is_active"]) == 1)

    def _save(self) -> None:
        username = self.username.text().strip()
        if not username:
            warn(self, "Validation", "Username is required.")
            return

        role = self.role.currentText()
        is_active = 1 if self.active.isChecked() else 0
        pw = self.password.text()

        if self.selected_id is None:
            if not pw:
                warn(self, "Validation", "Password is required for new users.")
                return
            exec1(
                self.conn,
                "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?,?,?,?,?)",
                (username, sha256_hex(pw), role, is_active, utc_now_iso()),
            )
        else:
            if int(self.selected_id) == int(self.current_user["id"]) and is_active != 1:
                warn(self, "Validation", "You cannot deactivate your own user.")
                return
            if pw:
                self.conn.execute(
                    "UPDATE users SET username=?, password_hash=?, role=?, is_active=? WHERE id=?",
                    (username, sha256_hex(pw), role, is_active, self.selected_id),
                )
            else:
                self.conn.execute(
                    "UPDATE users SET username=?, role=?, is_active=? WHERE id=?",
                    (username, role, is_active, self.selected_id),
                )
            self.conn.commit()
        self.refresh()

    def _delete(self) -> None:
        if self.selected_id is None:
            return
        if int(self.selected_id) == int(self.current_user["id"]):
            warn(self, "Validation", "You cannot delete your own user.")
            return
        from PyQt6.QtWidgets import QMessageBox

        if (
            QMessageBox.question(
                self,
                "Delete user",
                "Delete the selected user? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.conn.execute("DELETE FROM users WHERE id = ?", (self.selected_id,))
        self.conn.commit()
        self.refresh()

