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
from src.ui.widgets import money_edit, qty_edit, warn


class ProductsPage(QWidget):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn
        self.selected_id: int | None = None
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search by SKU or name…")
        self.query.textChanged.connect(lambda _t: self.refresh())

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "SKU", "Name", "Unit", "Price", "Cost", "Stock"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.sku = QLineEdit()
        self.name = QLineEdit()
        self.unit = QLineEdit()
        self.unit.setPlaceholderText("pcs")
        self.price = money_edit()
        self.cost = money_edit()
        self.stock = qty_edit()

        form = QFormLayout()
        form.addRow("SKU", self.sku)
        form.addRow("Name*", self.name)
        form.addRow("Unit", self.unit)
        form.addRow("Price", self.price)
        form.addRow("Cost", self.cost)
        form.addRow("Stock", self.stock)

        box = QGroupBox("Product")
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
        top.addWidget(QLabel("Products"))
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
            "SELECT id, sku, name, unit, price, cost, stock "
            "FROM products "
            "WHERE (? = '' OR COALESCE(sku,'') LIKE '%'||?||'%' OR name LIKE '%'||?||'%') "
            "ORDER BY id DESC",
            (needle, needle, needle),
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["id"],
                row["sku"] or "",
                row["name"],
                row["unit"],
                f'{float(row["price"]):.2f}',
                f'{float(row["cost"]):.2f}',
                f'{float(row["stock"]):.3f}'.rstrip("0").rstrip("."),
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self._new()

    def _new(self) -> None:
        self.selected_id = None
        self.sku.setText("")
        self.name.setText("")
        self.unit.setText("pcs")
        self.price.setText("0.00")
        self.cost.setText("0.00")
        self.stock.setText("0")
        self.table.clearSelection()

    def _on_select(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        rid = int(self.table.item(items[0].row(), 0).text())
        row = self.conn.execute(
            "SELECT id, sku, name, unit, price, cost, stock FROM products WHERE id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            return
        self.selected_id = int(row["id"])
        self.sku.setText(row["sku"] or "")
        self.name.setText(row["name"])
        self.unit.setText(row["unit"] or "pcs")
        self.price.setText(f'{float(row["price"]):.2f}')
        self.cost.setText(f'{float(row["cost"]):.2f}')
        self.stock.setText(str(row["stock"]))

    def _save(self) -> None:
        name = self.name.text().strip()
        if not name:
            warn(self, "Validation", "Name is required.")
            return
        sku = self.sku.text().strip() or None
        unit = self.unit.text().strip() or "pcs"
        price = float(self.price.text() or 0)
        cost = float(self.cost.text() or 0)
        stock = float(self.stock.text() or 0)

        if self.selected_id is None:
            exec1(
                self.conn,
                "INSERT INTO products (sku, name, unit, price, cost, stock, created_at) VALUES (?,?,?,?,?,?,?)",
                (sku, name, unit, price, cost, stock, utc_now_iso()),
            )
        else:
            self.conn.execute(
                "UPDATE products SET sku=?, name=?, unit=?, price=?, cost=?, stock=? WHERE id=?",
                (sku, name, unit, price, cost, stock, self.selected_id),
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
                "Delete product",
                "Delete the selected product? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.conn.execute("DELETE FROM products WHERE id = ?", (self.selected_id,))
        self.conn.commit()
        self.refresh()

