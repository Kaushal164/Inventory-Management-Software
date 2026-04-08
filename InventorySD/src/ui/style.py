from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication


def app_stylesheet() -> str:
    # Dark, modern “pro app” theme (high contrast, low glare).
    return """
QWidget {
  font-size: 13px;
  color: #e8ecf4;
}

QMainWindow {
  background: #0f131a;
}

QGroupBox {
  border: 1px solid #263042;
  border-radius: 12px;
  margin-top: 10px;
  background: #121826;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 6px;
  color: #cfd7e6;
  font-weight: 700;
}

QLineEdit, QComboBox, QDateEdit {
  padding: 9px 10px;
  border: 1px solid #2a3448;
  border-radius: 10px;
  background: #0b1220;
  selection-background-color: #2f6bff;
  selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
  border: 1px solid #5b8cff;
}

QPushButton {
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid #2a3448;
  background: #131b2b;
}
QPushButton:hover {
  background: #18243a;
  border: 1px solid #3a4a66;
}
QPushButton:pressed {
  background: #0b1220;
}
QPushButton#primaryButton {
  background: #2f6bff;
  border: 1px solid #2f6bff;
  color: #ffffff;
  font-weight: 800;
}
QPushButton#primaryButton:hover { background: #245cff; border-color: #245cff; }
QPushButton#dangerButton {
  background: #2a1216;
  border: 1px solid #5a1d24;
  color: #ffb4b4;
  font-weight: 800;
}

QMenuBar {
  background: #0f131a;
  border-bottom: 1px solid #263042;
}
QMenuBar::item {
  padding: 6px 10px;
  background: transparent;
}
QMenuBar::item:selected { background: #18243a; border-radius: 8px; }
QMenu {
  background: #121826;
  border: 1px solid #263042;
}
QMenu::item { padding: 8px 14px; }
QMenu::item:selected { background: #18243a; }

QToolBar {
  background: #0f131a;
  border-bottom: 1px solid #263042;
  spacing: 6px;
}

QTableWidget {
  background: #121826;
  border: 1px solid #263042;
  border-radius: 12px;
  gridline-color: #1c2638;
  selection-background-color: #1c3f9e;
  selection-color: #ffffff;
  alternate-background-color: #0f1626;
}
QHeaderView::section {
  background: #0b1220;
  border: none;
  border-bottom: 1px solid #263042;
  padding: 8px 10px;
  font-weight: 800;
  color: #cfd7e6;
}
QTableCornerButton::section {
  background: #0b1220;
  border: 0px;
}

QListWidget#sidebarNav {
  background: #0f1626;
  border: 1px solid #263042;
  border-radius: 14px;
  padding: 6px;
}
QListWidget#sidebarNav::item {
  margin: 3px;
  border-radius: 12px;
}
QListWidget#sidebarNav::item:selected {
  background: #18243a;
  border: 1px solid #2a3957;
}
QWidget#sidebarRow {
  background: transparent;
}
QLabel#sidebarLabel {
  color: #e8ecf4;
  font-weight: 800;
}
QLabel#sidebarBadge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #2a1216;
  border: 1px solid #5a1d24;
  color: #ffb4b4;
  font-weight: 900;
}

QLabel#pageTitle {
  font-size: 18px;
  font-weight: 900;
  color: #e8ecf4;
}
QLabel#userChip {
  padding: 6px 10px;
  border-radius: 999px;
  background: #131b2b;
  border: 1px solid #263042;
  color: #cfd7e6;
  font-weight: 700;
}

QScrollBar:vertical {
  background: transparent;
  width: 12px;
  margin: 0px;
}
QScrollBar::handle:vertical {
  background: #263042;
  border-radius: 6px;
  min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #33415a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
  background: transparent;
  height: 12px;
  margin: 0px;
}
QScrollBar::handle:horizontal {
  background: #263042;
  border-radius: 6px;
  min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #33415a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QStatusBar {
  background: #0f131a;
  border-top: 1px solid #263042;
}

QMessageBox, QDialog, QWizard {
  background: #0f131a;
}

QCalendarWidget QWidget {
  alternate-background-color: #121826;
}
"""


def apply_app_style(app: QApplication) -> None:
    f = QFont()
    f.setFamily("Segoe UI")
    app.setFont(f)
    app.setStyleSheet(app_stylesheet())

