import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set.")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price NUMERIC(10, 2) NOT NULL,
        stock_count INTEGER NOT NULL DEFAULT 0,
        specs TEXT,
        image_url TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        telegram_user_id BIGINT NOT NULL,
        customer_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        delivery_notes TEXT,
        payment_method TEXT NOT NULL,
        payment_reference TEXT,
        payment_status TEXT NOT NULL DEFAULT 'PENDING',
        order_status TEXT NOT NULL DEFAULT 'NEW',
        total_amount NUMERIC(10, 2) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        quantity INTEGER NOT NULL,
        unit_price NUMERIC(10, 2) NOT NULL,
        subtotal NUMERIC(10, 2) NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def add_product(name: str, category: str, price: float, stock_count: int, specs: str, image_url: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, category, price, stock_count, specs, image_url, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        RETURNING id;
    """, (name, category, price, stock_count, specs, image_url))
    new_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return new_id

def delete_product(product_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE products 
        SET is_active = FALSE 
        WHERE id = %s RETURNING id;
    """, (product_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row is not None

def get_active_products() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, category, price, stock_count, specs, image_url 
        FROM products 
        WHERE is_active = TRUE 
        ORDER BY id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        item = dict(row)
        item["price"] = float(item["price"])
        products.append(item)
    return products

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
    now = datetime.now(timezone.utc)
    
    try:
        total_amount = 0.0
        for item in items:
            cursor.execute("SELECT price, stock_count FROM products WHERE id = %s AND is_active = TRUE", (item["product_id"],))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product ID {item['product_id']} not found or inactive.")
            if row["stock_count"] < item["quantity"]:
                raise ValueError(f"Insufficient stock for product ID {item['product_id']}.")
            total_amount += float(row["price"]) * item["quantity"]

        cursor.execute("""
            INSERT INTO orders (
                telegram_user_id, customer_name, phone_number,
                delivery_address, delivery_notes, payment_method,
                total_amount, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            telegram_user_id, customer_name, phone_number,
            delivery_address, delivery_notes, payment_method,
            total_amount, now, now
        ))
        order_id = cursor.fetchone()["id"]

        for item in items:
            cursor.execute("SELECT price FROM products WHERE id = %s", (item["product_id"],))
            unit_price = float(cursor.fetchone()["price"])
            subtotal = unit_price * item["quantity"]
            
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (order_id, item["product_id"], item["quantity"], unit_price, subtotal))
            
            cursor.execute("""
                UPDATE products 
                SET stock_count = stock_count - %s 
                WHERE id = %s
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
    cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    order_row = cursor.fetchone()
    if not order_row:
        conn.close()
        return None
    
    order = dict(order_row)
    cursor.execute("""
        SELECT oi.*, p.name as product_name 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (order_id,))
    order["items"] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return order

def update_payment_ref(order_id: int, ref_code: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    cursor.execute("""
        UPDATE orders 
        SET payment_reference = %s, payment_status = 'SUBMITTED', updated_at = %s
        WHERE id = %s
    """, (ref_code, now, order_id))
    conn.commit()
    conn.close()
