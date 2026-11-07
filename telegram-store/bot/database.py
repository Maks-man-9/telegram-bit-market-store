import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Reliable path inside the bot directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        specs TEXT,
        stock_count INTEGER NOT NULL DEFAULT 0,
        image_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        delivery_notes TEXT,
        payment_method TEXT NOT NULL,
        payment_reference TEXT,
        payment_status TEXT NOT NULL DEFAULT 'PENDING',
        order_status TEXT NOT NULL DEFAULT 'NEW',
        total_amount REAL NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)
    conn.commit()

    # Automatically seed the initial inventory if empty
    cursor.execute("SELECT COUNT(*) as count FROM products")
    if cursor.fetchone()["count"] == 0:
        default_items = [
            (1, "CHG-65W-GAN", "65W GaN Dual USB-C Fast Charger", "Chargers", 38.99, json.dumps({"Ports": "2x USB-C, 1x USB-A", "Tech": "GaN III", "Power": "65W Max"}), 25, "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"),
            (2, "CBL-TB4-2M", "Braided Thunderbolt 4 / USB-C Cable (2m)", "Cables", 24.50, json.dumps({"Bandwidth": "40Gbps", "Length": "2 meters", "Power": "100W PD"}), 50, "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80"),
            (3, "SSD-NVME-1TB", "Rugged Portable NVMe SSD (1TB)", "Storage", 109.00, json.dumps({"Read Speed": "1050 MB/s", "Durability": "IP55 Water/Dust", "Interface": "USB 3.2 Gen 2"}), 14, "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&auto=format&fit=crop&q=80"),
            (4, "AUD-ANC-PRO", "Hi-Res Wireless ANC Earbuds", "Audio Gear", 89.95, json.dumps({"ANC": "Hybrid Active", "Battery": "32h total", "Codec": "LDAC / AAC"}), 18, "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"),
            (5, "ADP-8IN1-HUB", "8-in-1 Aluminium USB-C Hub Adapter", "Adapters", 45.00, json.dumps({"HDMI": "4K @ 60Hz", "Ethernet": "Gigabit", "Card Reader": "SD/TF"}), 30, "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=600&auto=format&fit=crop&q=80")
        ]
        cursor.executemany("""
        INSERT INTO products (id, sku, name, category, price, specs, stock_count, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_items)
        conn.commit()

    conn.close()

def create_order(
    telegram_user_id: int,
    customer_name: str,
    phone_number: str,
    delivery_address: str,
    delivery_notes: str,
    payment_method: str,
    items: List[Dict[str, Any]]
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        total_amount = 0.0
        for item in items:
            cursor.execute("SELECT price, stock_count FROM products WHERE id = ?", (item["product_id"],))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product ID {item['product_id']} not found.")
            if row["stock_count"] < item["quantity"]:
                raise ValueError(f"Insufficient stock for product ID {item['product_id']}.")
            total_amount += row["price"] * item["quantity"]

        cursor.execute("""
            INSERT INTO orders (
                telegram_user_id, customer_name, phone_number,
                delivery_address, delivery_notes, payment_method,
                total_amount, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_user_id, customer_name, phone_number,
            delivery_address, delivery_notes, payment_method,
            total_amount, now, now
        ))
        order_id = cursor.lastrowid

        for item in items:
            cursor.execute("SELECT price FROM products WHERE id = ?", (item["product_id"],))
            unit_price = cursor.fetchone()["price"]
            subtotal = unit_price * item["quantity"]
            
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, item["product_id"], item["quantity"], unit_price, subtotal))
            
            cursor.execute("""
                UPDATE products 
                SET stock_count = stock_count - ? 
                WHERE id = ?
            """, (item["quantity"], item["product_id"]))

        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order_row = cursor.fetchone()
    if not order_row:
        conn.close()
        return None
    
    order = dict(order_row)
    cursor.execute("""
        SELECT oi.*, p.name as product_name, p.sku 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    """, (order_id,))
    order["items"] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return order

def update_payment_ref(order_id: int, ref_code: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE orders 
        SET payment_reference = ?, payment_status = 'SUBMITTED', updated_at = ?
        WHERE id = ?
    """, (ref_code, now, order_id))
    conn.commit()
    conn.close()
