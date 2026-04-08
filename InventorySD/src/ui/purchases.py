from __future__ import annotations

import sqlite3
from dataclasses import dataclass

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
class PurchaseItemDraft:
    product_id: int
    description: str
    qty: float
    unit_cost: float

    @property
    def line_total(self) -> float:
        return float(self.qty) * float(self.unit_cost)


class PurchasesPage(QWidget):
    def __init__(self, conn: sqlite3.Connection, user: dict):
        super().__init__()
        self.conn = conn
        self.user = user
        self.draft_items: list[PurchaseItemDraft] = []

        self.p_table = QTableWidget(0, 5)
        self.p_table.setHorizontalHeaderLabels(["ID", "Bill", "Supplier", "Created At", "Total"])
        self.p_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.p_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.p_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.p_table.setAlternatingRowColors(True)
        self.p_table.verticalHeader().setVisible(False)
        self.p_table.horizontalHeader().setStretchLastSection(True)
        self.p_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.bill = QLineEdit()
        self.supplier = QLineEdit()

        header_form = QFormLayout()
        header_form.addRow("Bill No", self.bill)
        header_form.addRow("Supplier", self.supplier)
        header_box = QGroupBox("New Purchase")
        header_box.setLayout(header_form)

        self.product_pick = NoWheelComboBox()
        make_searchable_combo(self.product_pick, "Type product name…")
        self.qty = qty_edit()
        self.qty.setText("1")
        self.unit_cost = money_edit()
        self.desc = QLineEdit()
        self.product_pick.currentIndexChanged.connect(self._prefill_cost)

        add_form = QFormLayout()
        add_form.addRow("Product", self.product_pick)
        add_form.addRow("Qty", self.qty)
        add_form.addRow("Unit Cost", self.unit_cost)
        add_form.addRow("Description", self.desc)
        add_box = QGroupBox("Add Item")
        add_box.setLayout(add_form)

        btn_add = QPushButton("Add to Draft")
        btn_remove = QPushButton("Remove Selected Draft Item")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self._add_draft_item)
        btn_remove.clicked.connect(self._remove_draft_item)

        self.draft_table = QTableWidget(0, 5)
        self.draft_table.setHorizontalHeaderLabels(["Product ID", "Name", "Qty", "Unit Cost", "Line Total"])
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
        btn_save = QPushButton("Save Purchase")
        btn_refresh = QPushButton("Refresh Purchases")
        btn_save.setObjectName("primaryButton")
        btn_new.clicked.connect(self._clear_draft)
        btn_save.clicked.connect(self._save_purchase)
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
        left.addWidget(self.p_table, 1)

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

        self._reload_products()
        self.refresh()

    def _reload_products(self) -> None:
        self.product_pick.clear()
        rows = q(self.conn, "SELECT id, name, cost FROM products ORDER BY name")
        for row in rows:
            self.product_pick.addItem(f'{row["name"]} (#{row["id"]})', int(row["id"]))
        self._prefill_cost()

    def _prefill_cost(self) -> None:
        pid = self.product_pick.currentData()
        if pid is None:
            return
        row = self.conn.execute("SELECT cost FROM products WHERE id = ?", (int(pid),)).fetchone()
        if row is None:
            return
        self.unit_cost.setText(f'{float(row["cost"]):.2f}')

    def refresh(self) -> None:
        rows = q(
            self.conn,
            "SELECT id, bill_no, supplier_name, created_at, total FROM purchases ORDER BY id DESC LIMIT 200",
        )
        self.p_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row["id"],
                row["bill_no"] or "",
                row["supplier_name"] or "",
                row["created_at"],
                f'{float(row["total"]):.2f}',
            ]
            for c, v in enumerate(vals):
                self.p_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.p_table.resizeColumnsToContents()
        self._reload_products()

    def _add_draft_item(self) -> None:
        pid = self.product_pick.currentData()
        if pid is None:
            warn(self, "Missing", "Create a product first.")
            return
        qty = float(self.qty.text() or 0)
        if qty <= 0:
            warn(self, "Validation", "Qty must be > 0.")
            return
        unit_cost = float(self.unit_cost.text() or 0)
        row = self.conn.execute("SELECT name FROM products WHERE id = ?", (int(pid),)).fetchone()
        if row is None:
            return
        name = str(row["name"])

        d = PurchaseItemDraft(
            product_id=int(pid),
            description=self.desc.text().strip() or name,
            qty=qty,
            unit_cost=unit_cost,
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
            row = self.conn.execute("SELECT name FROM products WHERE id = ?", (it.product_id,)).fetchone()
            name = str(row["name"]) if row else it.description
            vals = [it.product_id, name, f"{it.qty:g}", f"{it.unit_cost:.2f}", f"{it.line_total:.2f}"]
            for c, v in enumerate(vals):
                self.draft_table.setItem(r, c, QTableWidgetItem(str(v)))
        self.draft_table.resizeColumnsToContents()
        self.total_label.setText(f"Total: {total:.2f}")

    def _clear_draft(self) -> None:
        self.bill.setText("")
        self.supplier.setText("")
        self.desc.setText("")
        self.qty.setText("1")
        self.draft_items = []
        self._render_draft()

    def _save_purchase(self) -> None:
        if not self.draft_items:
            warn(self, "Validation", "Add at least one item.")
            return
        total = sum(i.line_total for i in self.draft_items)
        purchase_id = exec1(
            self.conn,
            "INSERT INTO purchases (bill_no, supplier_name, created_by, created_at, total) VALUES (?,?,?,?,?)",
            (
                self.bill.text().strip() or None,
                self.supplier.text().strip() or None,
                int(self.user["id"]),
                utc_now_iso(),
                float(total),
            ),
        )
        for it in self.draft_items:
            exec1(
                self.conn,
                "INSERT INTO purchase_items (purchase_id, product_id, description, qty, unit_cost, line_total) "
                "VALUES (?,?,?,?,?,?)",
                (purchase_id, it.product_id, it.description, it.qty, it.unit_cost, it.line_total),
            )
            # Purchases increase stock.
            self.conn.execute("UPDATE products SET stock = stock + ?, cost = ? WHERE id = ?", (it.qty, it.unit_cost, it.product_id))
        self.conn.commit()
        self._clear_draft()
        self.refresh()

