import json
from database import init_db, get_connection

SAMPLE_PRODUCTS = [
    {
        "sku": "CHG-65W-GAN",
        "name": "65W GaN Dual USB-C Fast Charger",
        "category": "Chargers",
        "price": 38.99,
        "specs": json.dumps({"Ports": "2x USB-C, 1x USB-A", "Tech": "GaN III", "Power": "65W Max"}),
        "stock_count": 25,
        "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "CBL-TB4-2M",
        "name": "Braided Thunderbolt 4 / USB-C Cable (2m)",
        "category": "Cables",
        "price": 24.50,
        "specs": json.dumps({"Bandwidth": "40Gbps", "Length": "2 meters", "Power": "100W PD"}),
        "stock_count": 50,
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "SSD-NVME-1TB",
        "name": "Rugged Portable NVMe SSD (1TB)",
        "category": "Storage",
        "price": 109.00,
        "specs": json.dumps({"Read Speed": "1050 MB/s", "Durability": "IP55 Water/Dust", "Interface": "USB 3.2 Gen 2"}),
        "stock_count": 14,
        "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "AUD-ANC-PRO",
        "name": "Hi-Res Wireless ANC Earbuds",
        "category": "Audio Gear",
        "price": 89.95,
        "specs": json.dumps({"ANC": "Hybrid Active", "Battery": "32h total", "Codec": "LDAC / AAC"}),
        "stock_count": 18,
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "ADP-8IN1-HUB",
        "name": "8-in-1 Aluminium USB-C Hub Adapter",
        "category": "Adapters",
        "price": 45.00,
        "specs": json.dumps({"HDMI": "4K @ 60Hz", "Ethernet": "Gigabit", "Card Reader": "SD/TF"}),
        "stock_count": 30,
        "image_url": "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=600&auto=format&fit=crop&q=80"
    }
]

def seed():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    for p in SAMPLE_PRODUCTS:
        cursor.execute("""
            INSERT OR REPLACE INTO products (sku, name, category, price, specs, stock_count, image_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (p["sku"], p["name"], p["category"], p["price"], p["specs"], p["stock_count"], p["image_url"]))
    conn.commit()
    conn.close()
    print("Database schema verified and seeded with initial catalog.")

if __name__ == "__main__":
    seed()
