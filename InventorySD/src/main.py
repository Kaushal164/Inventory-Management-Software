from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.db import connect, default_config, init_db
from src.ui.login import LoginDialog
from src.ui.main_window import MainWindow
from src.ui.style import apply_app_style


def main() -> int:
    app = QApplication(sys.argv)
    apply_app_style(app)

    cfg = default_config()
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(cfg.db_path)
    init_db(conn)

    login = LoginDialog(conn)
    if login.exec() != login.DialogCode.Accepted:
        return 0

    user = login.user
    if user is None:
        return 0

    win = MainWindow(conn, user)
    win.resize(1100, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

