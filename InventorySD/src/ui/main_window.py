from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.ui.products import ProductsPage
from src.ui.purchases import PurchasesPage
from src.ui.reports import ReportsPage
from src.ui.sales import SalesPage
from src.ui.services import ServicesPage
from src.ui.users import UsersPage
from src.ui.wizards import NewPurchaseWizard, NewSaleWizard


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, user: dict):
        super().__init__()
        self.conn = conn
        self.user = user

        self.setWindowTitle("InventorySD")
        self.statusBar().showMessage("Ready")

        # Toolbar (pro feel: consistent global actions + shortcuts)
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        act_refresh = QAction(self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload), "Refresh", self)
        act_refresh.setShortcut(QKeySequence.StandardKey.Refresh)
        act_refresh.triggered.connect(self._refresh_current_page)
        tb.addAction(act_refresh)

        act_new_sale = QAction(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton), "New Sale", self)
        act_new_sale.setShortcut(QKeySequence("Ctrl+N"))
        act_new_sale.triggered.connect(self._new_sale)
        tb.addAction(act_new_sale)

        act_new_purchase = QAction(
            self.style().standardIcon(self.style().StandardPixmap.SP_DialogSaveButton), "New Purchase", self
        )
        act_new_purchase.setShortcut(QKeySequence("Ctrl+Shift+N"))
        act_new_purchase.triggered.connect(self._new_purchase)
        tb.addAction(act_new_purchase)

        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        tb.addSeparator()
        tb.addAction(act_about)

        # Sidebar + stacked pages
        self.nav = QListWidget()
        self.nav.setObjectName("sidebarNav")
        self.nav.setFixedWidth(210)
        self.nav.setSpacing(2)
        self.nav.setAlternatingRowColors(False)
        # Styling is handled by global stylesheet in src/ui/style.py

        self.pages = QStackedWidget()
        self.page_title = QLabel("")
        self.page_title.setObjectName("pageTitle")

        self.user_chip = QLabel(f"{user['username']} · {user['role']}")
        self.user_chip.setObjectName("userChip")

        header = QHBoxLayout()
        header.addWidget(self.page_title)
        header.addStretch(1)
        header.addWidget(self.user_chip)

        header_wrap = QFrame()
        header_wrap.setStyleSheet("QFrame { background: transparent; }")
        header_wrap.setLayout(header)

        content = QVBoxLayout()
        content.addWidget(header_wrap)
        content.addWidget(self.pages, 1)

        content_wrap = QWidget()
        content_wrap.setLayout(content)

        root = QHBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        root.addWidget(self.nav, 0)
        root.addWidget(content_wrap, 1)

        root_wrap = QWidget()
        root_wrap.setLayout(root)
        self.setCentralWidget(root_wrap)

        # Register pages
        self.page_dashboard = ReportsPage(conn)
        self.page_sales = SalesPage(conn, user)
        self.page_purchases = PurchasesPage(conn, user)
        self.page_products = ProductsPage(conn)
        self.page_services = ServicesPage(conn)
        self.page_users = UsersPage(conn, user)

        # Sidebar entries
        self._add_nav_page("Dashboard", self.page_dashboard, self.style().StandardPixmap.SP_ComputerIcon)
        self._add_nav_page("Sales", self.page_sales, self.style().StandardPixmap.SP_DialogApplyButton)
        self._add_nav_page("Purchases", self.page_purchases, self.style().StandardPixmap.SP_DialogSaveButton)
        self._add_nav_page("Products", self.page_products, self.style().StandardPixmap.SP_FileDialogContentsView)
        self._add_nav_page("Services", self.page_services, self.style().StandardPixmap.SP_FileDialogDetailedView)
        self._add_nav_page("Users", self.page_users, self.style().StandardPixmap.SP_DirHomeIcon)

        self.nav.currentRowChanged.connect(self._set_current_index)
        self.nav.setCurrentRow(0)

        # Minimal menu (keep it simple but “app-like”)
        menu_help = self.menuBar().addMenu("Help")
        menu_help.addAction(act_about)

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "InventorySD\n\nPython + PyQt6 + SQLite\nDefault login: admin / admin123",
        )

    def _add_nav_page(self, label: str, widget: QWidget, icon: object | None = None) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, label)
        if icon is not None:
            item.setIcon(self.style().standardIcon(icon))
        item.setSizeHint(item.sizeHint() * 1.2)
        self.nav.addItem(item)

        row = QWidget()
        row.setObjectName("sidebarRow")
        lay = QHBoxLayout()
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)
        t = QLabel(label)
        t.setObjectName("sidebarLabel")
        lay.addWidget(t)
        lay.addStretch(1)
        row.setLayout(lay)
        self.nav.setItemWidget(item, row)

        self.pages.addWidget(widget)

    def _set_current_index(self, idx: int) -> None:
        if idx < 0 or idx >= self.pages.count():
            return
        self.pages.setCurrentIndex(idx)
        label = self.nav.item(idx).data(Qt.ItemDataRole.UserRole) or "Page"
        self.page_title.setText(str(label))
        self.statusBar().showMessage(f"Viewing {label}")

    def _refresh_current_page(self) -> None:
        w = self.pages.currentWidget()
        if w is None:
            return
        # Convention: pages expose refresh()
        refresh = getattr(w, "refresh", None)
        if callable(refresh):
            refresh()
            self.statusBar().showMessage("Refreshed", 2000)

    def _new_sale(self) -> None:
        wiz = NewSaleWizard(self.conn, self.user, self)
        if wiz.exec() == wiz.DialogCode.Accepted:
            self.page_sales.refresh()
            self.page_products.refresh()
            self.page_dashboard.refresh()
            self.statusBar().showMessage("Sale saved", 2500)

    def _new_purchase(self) -> None:
        wiz = NewPurchaseWizard(self.conn, self.user, self)
        if wiz.exec() == wiz.DialogCode.Accepted:
            self.page_purchases.refresh()
            self.page_products.refresh()
            self.page_dashboard.refresh()
            self.statusBar().showMessage("Purchase saved", 2500)

