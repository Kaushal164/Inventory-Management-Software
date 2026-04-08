from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
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

from src.db import exec1, q, utc_now_iso
from src.ui.widgets import NoWheelComboBox, make_searchable_combo, money_edit, qty_edit, warn


@dataclass
class SaleItemDraft:
    item_type: str  # product|service
    item_id: int
    description: str
    qty: float
    unit_price: float

    @property
    def line_total(self) -> float:
        return float(self.qty) * float(self.unit_price)


class SalesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection, user: dict):
        super().__init__()
        self.conn = conn
        self.user = user
        self.draft_items: list[SaleItemDraft] = []

        # List of existing sales
        self.sales_table = QTableWidget(0, 5)
        self.sales_table.setHorizontalHeaderLabels(["ID", "Invoice", "Customer", "Created At", "Total"])
        self.sales_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sales_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.horizontalHeader().setStretchLastSection(True)
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Draft header
        self.invoice = QLineEdit()
        self.customer = QLineEdit()

        header_form = QFormLayout()
        header_form.addRow("Invoice No", self.invoice)
        header_form.addRow("Customer", self.customer)
        header_box = QGroupBox("New Sale")
        header_box.setLayout(header_form)

        # Draft item adder
        self.item_type = NoWheelComboBox()
        self.item_type.addItems(["product", "service"])
        self.item_pick = NoWheelComboBox()
        make_searchable_combo(self.item_pick, "Type product/service name…")
        self.qty = qty_edit()
        self.qty.setText("1")
        self.unit_price = money_edit()
        self.desc = QLineEdit()

        self.item_type.currentTextChanged.connect(self._reload_item_pick)
        self.item_pick.currentIndexChanged.connect(self._prefill_price_from_pick)

        add_form = QFormLayout()
        add_form.addRow("Type", self.item_type)
        add_form.addRow("Item", self.item_pick)
        add_form.addRow("Qty", self.qty)
        add_form.addRow("Unit Price", self.unit_price)
        add_form.addRow("Description", self.desc)
        add_box = QGroupBox("Add Item")
        add_box.setLayout(add_form)

        btn_add = QPushButton("Add to Draft")
        btn_remove = QPushButton("Remove Selected Draft Item")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self._add_draft_item)
        btn_remove.clicked.connect(self._remove_draft_item)

        # Draft items table
        self.draft_table = QTableWidget(0, 6)
        self.draft_table.setHorizontalHeaderLabels(["Type", "ID", "Name", "Qty", "Unit Price", "Line Total"])
        self.draft_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.draft_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.draft_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.draft_table.setAlternatingRowColors(True)
        self.draft_table.verticalHeader().setVisible(False)
        self.draft_table.horizontalHeader().setStretchLastSection(True)
        self.draft_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.total_label = QLabel("Total: 0.00")
        self.total_label.setStyleSheet("font-weight: 600; font-size: 14px;")

        btn_new = QPushButton("Clear Draft")
        btn_save = QPushButton("Save Sale")
        btn_refresh = QPushButton("Refresh Sales")
        btn_save.setObjectName("primaryButton")
        btn_new.clicked.connect(self._clear_draft)
        btn_save.clicked.connect(self._save_sale)
        btn_refresh.clicked.connect(self.refresh)

        actions = QHBoxLayout()
        actions.addWidget(btn_add)
        actions.addWidget(btn_remove)
        actions.addStretch(1)
        actions.addWidget(self.total_label)

        save_row = QHBoxLayout()
        save_row.addWidget(btn_new)
        save_row.addWidget(btn_save)
        save_row.addStretch(1)
        save_row.addWidget(btn_refresh)

        left = QVBoxLayout()
        left.addWidget(self.sales_table, 1)

        right = QVBoxLayout()
        right.addWidget(header_box)
        right.addWidget(add_box)
        right.addLayout(actions)
        right.addWidget(self.draft_table, 1)
        right.addLayout(save_row)

        root = QHBoxLayout()
        root.addLayout(left, 2)
        root.addLayout(right, 3)
        self.setLayout(root)

        self._reload_item_pick()
        self.refresh()

    def refresh(self) -> None:
        rows = q(
            self.conn,
            "SELECT id, invoice_no, customer_name, created_at, total FROM sales ORDER BY id DESC LIMIT 200",
        )
        self.sales_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["id"],
                row["invoice_no"] or "",
                row["customer_name"] or "",
                row["created_at"],
                f'{float(row["total"]):.2f}',
            ]
            for c, v in enumerate(vals):
                self.sales_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.sales_table.resizeColumnsToContents()

    def _reload_item_pick(self) -> None:
        t = self.item_type.currentText()
        self.item_pick.clear()
        if t == "product":
            rows = q(self.conn, "SELECT id, name, price FROM products ORDER BY name")
            for row in rows:
                self.item_pick.addItem(f'{row["name"]} (#{row["id"]})', int(row["id"]))
        else:
            rows = q(self.conn, "SELECT id, name, price FROM services ORDER BY name")
            for row in rows:
                self.item_pick.addItem(f'{row["name"]} (#{row["id"]})', int(row["id"]))
        self._prefill_price_from_pick()

    def _prefill_price_from_pick(self) -> None:
        t = self.item_type.currentText()
        item_id = self.item_pick.currentData()
        if item_id is None:
            return
        if t == "product":
            row = self.conn.execute("SELECT price, name FROM products WHERE id = ?", (int(item_id),)).fetchone()
        else:
            row = self.conn.execute("SELECT price, name FROM services WHERE id = ?", (int(item_id),)).fetchone()
        if row is None:
            return
        self.unit_price.setText(f'{float(row["price"]):.2f}')

    def _add_draft_item(self) -> None:
        t = self.item_type.currentText()
        item_id = self.item_pick.currentData()
        if item_id is None:
            warn(self, "Missing", "Create a product/service first.")
            return
        qty = float(self.qty.text() or 0)
        if qty <= 0:
            warn(self, "Validation", "Qty must be > 0.")
            return
        unit_price = float(self.unit_price.text() or 0)

        if t == "product":
            row = self.conn.execute("SELECT name FROM products WHERE id = ?", (int(item_id),)).fetchone()
        else:
            row = self.conn.execute("SELECT name FROM services WHERE id = ?", (int(item_id),)).fetchone()
        if row is None:
            return
        name = str(row["name"])

        d = SaleItemDraft(
            item_type=t,
            item_id=int(item_id),
            description=self.desc.text().strip() or name,
            qty=qty,
            unit_price=unit_price,
        )
        self.draft_items.append(d)
        self._render_draft()

    def _remove_draft_item(self) -> None:
        items = self.draft_table.selectedItems()
        if not items:
            return
        r = items[0].row()
        if 0 <= r < len(self.draft_items):
            self.draft_items.pop(r)
            self._render_draft()

    def _render_draft(self) -> None:
        self.draft_table.setRowCount(len(self.draft_items))
        total = 0.0
        for r, it in enumerate(self.draft_items):
            total += it.line_total
            vals = [
                it.item_type,
                it.item_id,
                it.description,
                f"{it.qty:g}",
                f"{it.unit_price:.2f}",
                f"{it.line_total:.2f}",
            ]
            for c, v in enumerate(vals):
                self.draft_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.draft_table.resizeColumnsToContents()
        self.total_label.setText(f"Total: {total:.2f}")

    def _clear_draft(self) -> None:
        self.invoice.setText("")
        self.customer.setText("")
        self.desc.setText("")
        self.qty.setText("1")
        self.draft_items = []
        self._render_draft()

    def _save_sale(self) -> None:
        if not self.draft_items:
            warn(self, "Validation", "Add at least one item.")
            return
        total = sum(i.line_total for i in self.draft_items)
        sale_id = exec1(
            self.conn,
            "INSERT INTO sales (invoice_no, customer_name, created_by, created_at, total) VALUES (?,?,?,?,?)",
            (
                self.invoice.text().strip() or None,
                self.customer.text().strip() or None,
                int(self.user["id"]),
                utc_now_iso(),
                float(total),
            ),
        )
        for it in self.draft_items:
            exec1(
                self.conn,
                "INSERT INTO sale_items (sale_id, item_type, item_id, description, qty, unit_price, line_total) "
                "VALUES (?,?,?,?,?,?,?)",
                (sale_id, it.item_type, it.item_id, it.description, it.qty, it.unit_price, it.line_total),
            )
            # If selling a product, decrement stock.
            if it.item_type == "product":
                self.conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (it.qty, it.item_id))
        self.conn.commit()
        self._clear_draft()
        self.refresh()

