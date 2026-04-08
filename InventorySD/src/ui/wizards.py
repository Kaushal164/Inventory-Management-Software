from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
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


@dataclass
class PurchaseItemDraft:
    product_id: int
    description: str
    qty: float
    unit_cost: float

    @property
    def line_total(self) -> float:
        return float(self.qty) * float(self.unit_cost)


class _SaleHeaderPage(QWizardPage):
    def __init__(self, wizard: "NewSaleWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Sale details")
        self.setSubTitle("Enter customer and invoice information.")

        self.invoice = QLineEdit()
        self.customer = QLineEdit()

        form = QFormLayout()
        form.addRow("Invoice No", self.invoice)
        form.addRow("Customer", self.customer)
        self.setLayout(form)

    def validatePage(self) -> bool:
        self.wiz.invoice_no = self.invoice.text().strip() or None
        self.wiz.customer_name = self.customer.text().strip() or None
        return True


class _SaleItemsPage(QWizardPage):
    def __init__(self, wizard: "NewSaleWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Items")
        self.setSubTitle("Add products or services to the sale.")

        self.item_type = NoWheelComboBox()
        self.item_type.addItems(["product", "service"])
        self.item_pick = NoWheelComboBox()
        make_searchable_combo(self.item_pick, "Type product/service name…")
        self.qty = qty_edit()
        self.qty.setText("1")
        self.unit_price = money_edit()
        self.desc = QLineEdit()

        self.item_type.currentTextChanged.connect(self._reload_pick)
        self.item_pick.currentIndexChanged.connect(self._prefill_price)

        add_form = QFormLayout()
        add_form.addRow("Type", self.item_type)
        add_form.addRow("Item", self.item_pick)
        add_form.addRow("Qty", self.qty)
        add_form.addRow("Unit Price", self.unit_price)
        add_form.addRow("Description", self.desc)

        btn_add = QPushButton("Add item")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self._add)
        btn_remove = QPushButton("Remove selected")
        btn_remove.clicked.connect(self._remove)

        actions = QHBoxLayout()
        actions.addWidget(btn_add)
        actions.addWidget(btn_remove)
        actions.addStretch(1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Type", "ID", "Description", "Qty", "Unit Price", "Line Total"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        root = QVBoxLayout()
        root.addLayout(add_form)
        root.addLayout(actions)
        root.addWidget(self.table, 1)
        self.setLayout(root)

        self._reload_pick()

    def _reload_pick(self) -> None:
        t = self.item_type.currentText()
        self.item_pick.clear()
        if t == "product":
            rows = q(self.wiz.conn, "SELECT id, name, price FROM products ORDER BY name")
        else:
            rows = q(self.wiz.conn, "SELECT id, name, price FROM services ORDER BY name")
        for row in rows:
            self.item_pick.addItem(f'{row["name"]} (#{row["id"]})', int(row["id"]))
        self._prefill_price()

    def _prefill_price(self) -> None:
        t = self.item_type.currentText()
        item_id = self.item_pick.currentData()
        if item_id is None:
            self.unit_price.setText("0.00")
            return
        if t == "product":
            row = self.wiz.conn.execute("SELECT price, name FROM products WHERE id = ?", (int(item_id),)).fetchone()
        else:
            row = self.wiz.conn.execute("SELECT price, name FROM services WHERE id = ?", (int(item_id),)).fetchone()
        if row is None:
            return
        self.unit_price.setText(f'{float(row["price"]):.2f}')
        if not self.desc.text().strip():
            self.desc.setText(str(row["name"]))

    def _add(self) -> None:
        item_id = self.item_pick.currentData()
        if item_id is None:
            warn(self, "Missing", "Create a product/service first.")
            return
        qty = float(self.qty.text() or 0)
        if qty <= 0:
            warn(self, "Validation", "Qty must be > 0.")
            return
        unit_price = float(self.unit_price.text() or 0)
        d = SaleItemDraft(
            item_type=self.item_type.currentText(),
            item_id=int(item_id),
            description=self.desc.text().strip() or "",
            qty=qty,
            unit_price=unit_price,
        )
        self.wiz.items.append(d)
        self._render()

    def _remove(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        r = items[0].row()
        if 0 <= r < len(self.wiz.items):
            self.wiz.items.pop(r)
            self._render()

    def _render(self) -> None:
        self.table.setRowCount(len(self.wiz.items))
        for r, it in enumerate(self.wiz.items):
            vals = [
                it.item_type,
                it.item_id,
                it.description,
                f"{it.qty:g}",
                f"{it.unit_price:.2f}",
                f"{it.line_total:.2f}",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.table.resizeColumnsToContents()
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return len(self.wiz.items) > 0


class _SaleReviewPage(QWizardPage):
    def __init__(self, wizard: "NewSaleWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Review")
        self.setSubTitle("Confirm and save the sale.")
        self.summary = QLineEdit()
        self.summary.setReadOnly(True)
        form = QFormLayout()
        form.addRow("Summary", self.summary)
        self.setLayout(form)

    def initializePage(self) -> None:
        total = sum(i.line_total for i in self.wiz.items)
        self.summary.setText(f"{len(self.wiz.items)} items · Total {total:.2f}")


class NewSaleWizard(QWizard):
    def __init__(self, conn: sqlite3.Connection, user: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        self.invoice_no: str | None = None
        self.customer_name: str | None = None
        self.items: list[SaleItemDraft] = []

        self.setWindowTitle("New Sale")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.addPage(_SaleHeaderPage(self))
        self.addPage(_SaleItemsPage(self))
        self.addPage(_SaleReviewPage(self))

        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

    def accept(self) -> None:
        if not self.items:
            warn(self, "Validation", "Add at least one item.")
            return
        total = sum(i.line_total for i in self.items)
        sale_id = exec1(
            self.conn,
            "INSERT INTO sales (invoice_no, customer_name, created_by, created_at, total) VALUES (?,?,?,?,?)",
            (self.invoice_no, self.customer_name, int(self.user["id"]), utc_now_iso(), float(total)),
        )
        for it in self.items:
            exec1(
                self.conn,
                "INSERT INTO sale_items (sale_id, item_type, item_id, description, qty, unit_price, line_total) "
                "VALUES (?,?,?,?,?,?,?)",
                (sale_id, it.item_type, it.item_id, it.description, it.qty, it.unit_price, it.line_total),
            )
            if it.item_type == "product":
                self.conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (it.qty, it.item_id))
        self.conn.commit()
        super().accept()


class _PurchaseHeaderPage(QWizardPage):
    def __init__(self, wizard: "NewPurchaseWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Purchase details")
        self.setSubTitle("Enter supplier and bill information.")

        self.bill = QLineEdit()
        self.supplier = QLineEdit()

        form = QFormLayout()
        form.addRow("Bill No", self.bill)
        form.addRow("Supplier", self.supplier)
        self.setLayout(form)

    def validatePage(self) -> bool:
        self.wiz.bill_no = self.bill.text().strip() or None
        self.wiz.supplier_name = self.supplier.text().strip() or None
        return True


class _PurchaseItemsPage(QWizardPage):
    def __init__(self, wizard: "NewPurchaseWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Items")
        self.setSubTitle("Add products to the purchase.")

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

        btn_add = QPushButton("Add item")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self._add)
        btn_remove = QPushButton("Remove selected")
        btn_remove.clicked.connect(self._remove)

        actions = QHBoxLayout()
        actions.addWidget(btn_add)
        actions.addWidget(btn_remove)
        actions.addStretch(1)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Product ID", "Description", "Qty", "Unit Cost", "Line Total"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        root = QVBoxLayout()
        root.addLayout(add_form)
        root.addLayout(actions)
        root.addWidget(self.table, 1)
        self.setLayout(root)

        self._reload_products()

    def _reload_products(self) -> None:
        self.product_pick.clear()
        rows = q(self.wiz.conn, "SELECT id, name, cost FROM products ORDER BY name")
        for row in rows:
            self.product_pick.addItem(f'{row["name"]} (#{row["id"]})', int(row["id"]))
        self._prefill_cost()

    def _prefill_cost(self) -> None:
        pid = self.product_pick.currentData()
        if pid is None:
            self.unit_cost.setText("0.00")
            return
        row = self.wiz.conn.execute("SELECT cost, name FROM products WHERE id = ?", (int(pid),)).fetchone()
        if row is None:
            return
        self.unit_cost.setText(f'{float(row["cost"]):.2f}')
        if not self.desc.text().strip():
            self.desc.setText(str(row["name"]))

    def _add(self) -> None:
        pid = self.product_pick.currentData()
        if pid is None:
            warn(self, "Missing", "Create a product first.")
            return
        qty = float(self.qty.text() or 0)
        if qty <= 0:
            warn(self, "Validation", "Qty must be > 0.")
            return
        unit_cost = float(self.unit_cost.text() or 0)
        d = PurchaseItemDraft(
            product_id=int(pid),
            description=self.desc.text().strip() or "",
            qty=qty,
            unit_cost=unit_cost,
        )
        self.wiz.items.append(d)
        self._render()

    def _remove(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        r = items[0].row()
        if 0 <= r < len(self.wiz.items):
            self.wiz.items.pop(r)
            self._render()

    def _render(self) -> None:
        self.table.setRowCount(len(self.wiz.items))
        for r, it in enumerate(self.wiz.items):
            vals = [it.product_id, it.description, f"{it.qty:g}", f"{it.unit_cost:.2f}", f"{it.line_total:.2f}"]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.table.resizeColumnsToContents()
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return len(self.wiz.items) > 0


class _PurchaseReviewPage(QWizardPage):
    def __init__(self, wizard: "NewPurchaseWizard"):
        super().__init__(wizard)
        self.wiz = wizard
        self.setTitle("Review")
        self.setSubTitle("Confirm and save the purchase.")
        self.summary = QLineEdit()
        self.summary.setReadOnly(True)
        form = QFormLayout()
        form.addRow("Summary", self.summary)
        self.setLayout(form)

    def initializePage(self) -> None:
        total = sum(i.line_total for i in self.wiz.items)
        self.summary.setText(f"{len(self.wiz.items)} items · Total {total:.2f}")


class NewPurchaseWizard(QWizard):
    def __init__(self, conn: sqlite3.Connection, user: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self.user = user

        self.bill_no: str | None = None
        self.supplier_name: str | None = None
        self.items: list[PurchaseItemDraft] = []

        self.setWindowTitle("New Purchase")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.addPage(_PurchaseHeaderPage(self))
        self.addPage(_PurchaseItemsPage(self))
        self.addPage(_PurchaseReviewPage(self))

        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

    def accept(self) -> None:
        if not self.items:
            warn(self, "Validation", "Add at least one item.")
            return
        total = sum(i.line_total for i in self.items)
        purchase_id = exec1(
            self.conn,
            "INSERT INTO purchases (bill_no, supplier_name, created_by, created_at, total) VALUES (?,?,?,?,?)",
            (self.bill_no, self.supplier_name, int(self.user["id"]), utc_now_iso(), float(total)),
        )
        for it in self.items:
            exec1(
                self.conn,
                "INSERT INTO purchase_items (purchase_id, product_id, description, qty, unit_cost, line_total) "
                "VALUES (?,?,?,?,?,?)",
                (purchase_id, it.product_id, it.description, it.qty, it.unit_cost, it.line_total),
            )
            self.conn.execute(
                "UPDATE products SET stock = stock + ?, cost = ? WHERE id = ?",
                (it.qty, it.unit_cost, it.product_id),
            )
        self.conn.commit()
        super().accept()

