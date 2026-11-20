import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "orders.db"

ORDERS = [
    (1040, 1, "delivered", "2026-03-02", "2026-03-04"),
    (1041, 4, "processing", "2026-03-11", None),
    (1042, 3, "out for delivery", "2026-03-10", "2026-03-12"),
    (1043, 2, "shipped", "2026-03-13", "2026-03-14"),
    (1044, 5, "cancelled", "2026-03-14", None),
]


def create_database():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DROP TABLE IF EXISTS orders")
        conn.execute(
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT, "
            "order_date TEXT, shipped_date TEXT)"
        )
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)


def find_order(order_id):
    if not DB_FILE.exists():
        create_database()

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

    if row is None:
        return None
    return dict(row)


if __name__ == "__main__":
    create_database()
    print(f"Created {DB_FILE.name} with {len(ORDERS)} orders")
