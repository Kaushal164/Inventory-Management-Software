# InventorySD

A desktop Inventory Software built with Python, PyQt6, and SQLite.

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

-----> Use InventorySD in small businesses that need simple inventory + billing, for example:

Retail shop (mobile/parts/grocery)
Small warehouse/stock room
Service business (repairs, printing, salon, etc.)
Wholesale / supplier record keeping

It’s a Windows desktop app (offline) using a local SQLite database (inventory.db).

-----> How to use (basic workflow)

Login
Run python main.py

Login with:
admin
admin123

Step 1: Add Products / Services
Go to Products
Add product name, price, cost, stock
Go to Services
Add service name and price

Step 2: Record Purchases (stock in)
Go to Purchases or use New Purchase (toolbar)
Select product, quantity, unit cost
Save → stock increases

Step 3: Record Sales (stock out)
Go to Sales or use New Sale (toolbar)
Select product/service, quantity, unit price
Save → if it’s a product, stock decreases

Step 4: Reports + Export
Go to Dashboard
Choose date range (From/To)
Export CSV or PDF if needed

Step 5: Manage Users
Go to Users
Create staff users, set role, activate/deactivate, reset password

