from __future__ import annotations

# Root launcher for convenience:
#   python main.py
#
# The actual app lives in src/main.py and can also be run via:
#   python -m src.main

from src.main import main


if __name__ == "__main__":
    raise SystemExit(main())

