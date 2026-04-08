# InventorySD

A desktop **Inventory Software** built with **Python**, **PyQt6**, and **SQLite**.

## Main features
- Login + Users
- Products and Services management
- Sales and Purchases with line items
- Reports dashboard + export (CSV/PDF)

## Screens
- Dashboard (KPIs + recent sales)
- Products / Services (create, edit, delete)
- Sales / Purchases (quick entry + wizard)

## Default login
- Username: `admin`
- Password: `admin123`

## How to run (Windows / PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Database
The app creates `inventory.db` automatically on first run.

## Notes
- Stock updates automatically: **Purchases add stock**, **Sales reduce stock** (for products).
- To refresh a page, use the **Refresh** button (or `F5`).

