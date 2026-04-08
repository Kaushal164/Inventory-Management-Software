from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.db import verify_login


class LoginDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.user: dict | None = None

        self.setWindowTitle("InventorySD - Login")
        self.setModal(True)

        self.username = QLineEdit()
        self.username.setPlaceholderText("admin")
        self.password = QLineEdit()
        self.password.setPlaceholderText("admin123")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #b00020;")

        btn_login = QPushButton("Login")
        btn_cancel = QPushButton("Cancel")
        btn_login.clicked.connect(self._on_login)
        btn_cancel.clicked.connect(self.reject)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_login)

        root = QVBoxLayout()
        title = QLabel("Sign in")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)
        root.addLayout(form)
        root.addWidget(self.status)
        root.addLayout(btns)
        self.setLayout(root)

        self.username.setText("admin")
        self.password.setText("admin123")
        self.username.returnPressed.connect(self._on_login)
        self.password.returnPressed.connect(self._on_login)

    def _on_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self.status.setText("Enter username and password.")
            return

        user = verify_login(self.conn, username, password)
        if user is None:
            self.status.setText("Invalid credentials.")
            return

        self.user = user
        self.accept()

