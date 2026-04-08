from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QComboBox, QCompleter, QLineEdit, QMessageBox, QWidget


def money_edit() -> QLineEdit:
    e = QLineEdit()
    e.setValidator(QDoubleValidator(0.0, 1_000_000_000.0, 2))
    e.setPlaceholderText("0.00")
    return e


def qty_edit() -> QLineEdit:
    e = QLineEdit()
    e.setValidator(QDoubleValidator(0.0, 1_000_000_000.0, 3))
    e.setPlaceholderText("0")
    return e


def info(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def warn(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


class NoWheelComboBox(QComboBox):
    """Prevents accidental selection changes when scrolling the page."""

    def wheelEvent(self, e) -> None:  # type: ignore[override]
        if self.view().isVisible():
            super().wheelEvent(e)
        else:
            e.ignore()


def make_searchable_combo(cb: QComboBox, placeholder: str = "Type to search…") -> None:
    cb.setEditable(True)
    cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    cb.setMaxVisibleItems(14)
    cb.lineEdit().setPlaceholderText(placeholder)
    cb.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    cb.completer().setFilterMode(Qt.MatchFlag.MatchContains)
    cb.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)


