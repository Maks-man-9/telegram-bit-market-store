import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "store.db"

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
        specs TEXT, -- JSON string for key-value specs
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
        payment_method TEXT NOT NULL, -- 'COD' or 'MOBILE_MONEY'
        payment_reference TEXT,
        payment_status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, VERIFIED, FAILED
        order_status TEXT NOT NULL DEFAULT 'NEW',       -- NEW, CONFIRMED, DISPATCHED, DELIVERED, CANCELLED
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
    now = datetime.utcnow().isoformat()
    
    try:
        # Calculate total and verify inventory
        total_amount = 0.0
        for item in items:
            cursor.execute("SELECT price, stock_count FROM products WHERE id = ?", (item["product_id"],))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product ID {item['product_id']} not found.")
            if row["stock_count"] < item["quantity"]:
                raise ValueError(f"Insufficient stock for product ID {item['product_id']}.")
            total_amount += row["price"] * item["quantity"]

        # Insert Order
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

        # Insert Items & Decrement Stock
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
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        UPDATE orders 
        SET payment_reference = ?, payment_status = 'SUBMITTED', updated_at = ?
        WHERE id = ?
    """, (ref_code, now, order_id))
    conn.commit()
    conn.close()
