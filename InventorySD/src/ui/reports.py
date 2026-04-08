from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QDateEdit,
    QFileDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db import q


def _kpi_card(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setStyleSheet(
        """
        QFrame {
          background: #ffffff;
          border: 1px solid #d7dbe6;
          border-radius: 14px;
        }
        """
    )
    card.setMinimumHeight(88)
    t = QLabel(title)
    t.setStyleSheet("color: #5a6275; font-weight: 600;")
    v = QLabel("—")
    v.setStyleSheet("font-size: 22px; font-weight: 800; color: #1a1e2a;")
    v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    lay = QVBoxLayout()
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(6)
    lay.addWidget(t)
    lay.addWidget(v)
    lay.addStretch(1)
    card.setLayout(lay)
    return card, v


class ReportsPage(QWidget):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__()
        self.conn = conn

        # KPI dashboard cards
        self.card_products, self.v_products = _kpi_card("Products")
        self.card_services, self.v_services = _kpi_card("Services")
        self.card_sales, self.v_sales = _kpi_card("Sales (Total)")
        self.card_purchases, self.v_purchases = _kpi_card("Purchases (Total)")

        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.end_date.setCalendarPopup(True)
        today = date.today()
        # default: last 30 days (block signals during initial set)
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        self.end_date.setDate(today)
        self.start_date.setDate(date.fromordinal(today.toordinal() - 30))
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        self.start_date.dateChanged.connect(lambda _d: self.refresh())
        self.end_date.dateChanged.connect(lambda _d: self.refresh())

        self.top_products = QTableWidget(0, 3)
        self.top_products.setHorizontalHeaderLabels(["Product", "Stock", "Price"])
        self.top_products.setAlternatingRowColors(True)
        self.top_products.verticalHeader().setVisible(False)
        self.top_products.horizontalHeader().setStretchLastSection(True)
        self.top_products.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.recent_sales = QTableWidget(0, 4)
        self.recent_sales.setHorizontalHeaderLabels(["Invoice", "Customer", "Created At", "Total"])
        self.recent_sales.setAlternatingRowColors(True)
        self.recent_sales.verticalHeader().setVisible(False)
        self.recent_sales.horizontalHeader().setStretchLastSection(True)
        self.recent_sales.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("primaryButton")
        btn_refresh.clicked.connect(self.refresh)

        btn_csv = QPushButton("Export CSV")
        btn_pdf = QPushButton("Export PDF")
        btn_csv.clicked.connect(self.export_csv)
        btn_pdf.clicked.connect(self.export_pdf)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self.card_products, 0, 0)
        grid.addWidget(self.card_services, 0, 1)
        grid.addWidget(self.card_sales, 0, 2)
        grid.addWidget(self.card_purchases, 0, 3)
        root.addLayout(grid)

        actions = QHBoxLayout()
        actions.addWidget(QLabel("From"))
        actions.addWidget(self.start_date)
        actions.addWidget(QLabel("To"))
        actions.addWidget(self.end_date)
        actions.addStretch(1)
        actions.addWidget(btn_csv)
        actions.addWidget(btn_pdf)
        actions.addWidget(btn_refresh)
        root.addLayout(actions)

        row = QHBoxLayout()
        left = QVBoxLayout()
        l1 = QLabel("Low stock")
        l1.setStyleSheet("font-weight: 700; color: #1a1e2a;")
        left.addWidget(l1)
        left.addWidget(self.top_products)
        right = QVBoxLayout()
        l2 = QLabel("Recent sales")
        l2.setStyleSheet("font-weight: 700; color: #1a1e2a;")
        right.addWidget(l2)
        right.addWidget(self.recent_sales)
        row.addLayout(left, 1)
        row.addLayout(right, 2)

        root.addLayout(row, 1)
        self.setLayout(root)

        self.refresh()

    def refresh(self) -> None:
        start_iso, end_iso = self._date_range_iso()
        sales_sum = q(
            self.conn,
            "SELECT COALESCE(SUM(total),0) AS s FROM sales WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )[0]["s"]
        purchase_sum = q(
            self.conn,
            "SELECT COALESCE(SUM(total),0) AS s FROM purchases WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )[0]["s"]
        prod_count = q(self.conn, "SELECT COUNT(*) AS c FROM products")[0]["c"]
        svc_count = q(self.conn, "SELECT COUNT(*) AS c FROM services")[0]["c"]
        self.v_products.setText(str(int(prod_count)))
        self.v_services.setText(str(int(svc_count)))
        self.v_sales.setText(f"{float(sales_sum):.2f}")
        self.v_purchases.setText(f"{float(purchase_sum):.2f}")

        low = q(
            self.conn,
            "SELECT name, stock, price FROM products ORDER BY stock ASC, name ASC LIMIT 20",
        )
        self.top_products.setRowCount(len(low))
        for r, row in enumerate(low):
            vals = [row["name"], f'{float(row["stock"]):g}', f'{float(row["price"]):.2f}']
            for c, v in enumerate(vals):
                self.top_products.setItem(r, c, QTableWidgetItem(str(v)))
        self.top_products.resizeColumnsToContents()

        recent = q(
            self.conn,
            "SELECT invoice_no, customer_name, created_at, total "
            "FROM sales WHERE created_at BETWEEN ? AND ? "
            "ORDER BY id DESC LIMIT 50",
            (start_iso, end_iso),
        )
        self.recent_sales.setRowCount(len(recent))
        for r, row in enumerate(recent):
            vals = [
                row["invoice_no"] or "",
                row["customer_name"] or "",
                row["created_at"],
                f'{float(row["total"]):.2f}',
            ]
            for c, v in enumerate(vals):
                self.recent_sales.setItem(r, c, QTableWidgetItem(str(v)))
        self.recent_sales.resizeColumnsToContents()

    def _date_range_iso(self) -> tuple[str, str]:
        sd = self.start_date.date().toPyDate()
        ed = self.end_date.date().toPyDate()
        if ed < sd:
            sd, ed = ed, sd
        start_dt = datetime(sd.year, sd.month, sd.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(ed.year, ed.month, ed.day, 23, 59, 59, tzinfo=timezone.utc)
        return start_dt.isoformat(), end_dt.isoformat()

    def export_csv(self) -> None:
        start_iso, end_iso = self._date_range_iso()
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "inventory_report.csv", "CSV Files (*.csv)")
        if not path:
            return

        sales = q(
            self.conn,
            "SELECT invoice_no, customer_name, created_at, total FROM sales WHERE created_at BETWEEN ? AND ? ORDER BY id DESC",
            (start_iso, end_iso),
        )
        purchases = q(
            self.conn,
            "SELECT bill_no, supplier_name, created_at, total FROM purchases WHERE created_at BETWEEN ? AND ? ORDER BY id DESC",
            (start_iso, end_iso),
        )
        low = q(self.conn, "SELECT sku, name, stock, price FROM products ORDER BY stock ASC, name ASC LIMIT 50")

        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["InventorySD Report"])
            w.writerow(["From", start_iso])
            w.writerow(["To", end_iso])
            w.writerow([])

            w.writerow(["Sales"])
            w.writerow(["Invoice", "Customer", "Created At", "Total"])
            for r in sales:
                w.writerow([r["invoice_no"] or "", r["customer_name"] or "", r["created_at"], float(r["total"])])
            w.writerow([])

            w.writerow(["Purchases"])
            w.writerow(["Bill", "Supplier", "Created At", "Total"])
            for r in purchases:
                w.writerow([r["bill_no"] or "", r["supplier_name"] or "", r["created_at"], float(r["total"])])
            w.writerow([])

            w.writerow(["Low stock (top 50)"])
            w.writerow(["SKU", "Name", "Stock", "Price"])
            for r in low:
                w.writerow([r["sku"] or "", r["name"], float(r["stock"]), float(r["price"])])

    def export_pdf(self) -> None:
        start_iso, end_iso = self._date_range_iso()
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "inventory_report.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        sales_sum = q(
            self.conn,
            "SELECT COALESCE(SUM(total),0) AS s FROM sales WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )[0]["s"]
        purchase_sum = q(
            self.conn,
            "SELECT COALESCE(SUM(total),0) AS s FROM purchases WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )[0]["s"]

        html = f"""
        <h2>InventorySD Report</h2>
        <p><b>From:</b> {start_iso}<br/>
           <b>To:</b> {end_iso}</p>
        <h3>Summary</h3>
        <ul>
          <li><b>Sales total:</b> {float(sales_sum):.2f}</li>
          <li><b>Purchases total:</b> {float(purchase_sum):.2f}</li>
        </ul>
        <p style="color:#5a6275;">Generated by InventorySD</p>
        """

        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc.print(printer)
