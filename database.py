import sqlite3
from datetime import date
from translations import CATEGORY_KEY_MAP

def get_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            expiry_date TEXT,
            barcode TEXT
        )
    """)
    conn.commit()
    conn.close()

def calculate_status(expiry_date_str):
    expiry = date.fromisoformat(expiry_date_str)
    today = date.today()
    days_left = (expiry - today).days

    if days_left < 0:
        return {"code": "expired", "level": "expired", "days_left": days_left}
    elif days_left <= 1:
        return {"code": "urgent", "level": "urgent", "days_left": days_left}
    elif days_left <= 3:
        return {"code": "high", "level": "high", "days_left": days_left}
    elif days_left <= 7:
        return {"code": "week", "level": "medium", "days_left": days_left}
    elif days_left <= 14:
        return {"code": "two_week", "level": "medium", "days_left": days_left}
    elif days_left <= 30:
        return {"code": "month", "level": "low", "days_left": days_left}
    else:
        return {"code": "normal", "level": "normal", "days_left": days_left}

def get_all_items(search=None, category=None):
    conn = get_connection()
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY expiry_date ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(row)
        item["status"] = calculate_status(row["expiry_date"])
        items.append(item)

    return items

def delete_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_item_by_id(item_id):
    conn = get_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return item

def update_item(item_id, name, category, expiry_date):
    conn = get_connection()
    conn.execute(
        "UPDATE items SET name = ?, category = ?, expiry_date = ? WHERE id = ?",
        (name, category, expiry_date, item_id)
    )
    conn.commit()
    conn.close()

def get_dashboard_stats():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    total = len(rows)
    expired_count = 0
    urgent_count = 0

    category_counts = {}
    level_counts = {
        "expired": 0, "urgent": 0, "high": 0,
        "medium": 0, "low": 0, "normal": 0
    }

    for row in rows:
        status = calculate_status(row["expiry_date"])
        level = status["level"]

        level_counts[level] += 1

        if level == "expired":
            expired_count += 1
        if level in ("urgent", "high"):
            urgent_count += 1

        cat = row["category"] or "ไม่ระบุ"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total": total,
        "expired_count": expired_count,
        "urgent_count": urgent_count,
        "category_labels": list(category_counts.keys()),
        "category_values": list(category_counts.values()),
        "level_labels": list(level_counts.keys()),
        "level_values": list(level_counts.values())
    }

def get_recommendations(t):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    recommendations = []

    urgent_items = []
    expired_items = []
    category_expired_count = {}

    for row in rows:
        status = calculate_status(row["expiry_date"])
        level = status["level"]

        if level in ("urgent", "high"):
            urgent_items.append(row["name"])

        if level == "expired":
            expired_items.append(row["name"])
            cat = row["category"] or "ไม่ระบุ"
            category_expired_count[cat] = category_expired_count.get(cat, 0) + 1

    if urgent_items:
        names = "、".join(urgent_items[:3])
        recommendations.append({
            "type": "urgent",
            "message": t["rec_urgent"].format(count=len(urgent_items), names=names)
        })

    if expired_items:
        recommendations.append({
            "type": "expired",
            "message": t["rec_expired"].format(count=len(expired_items))
        })

    if category_expired_count:
        worst_category = max(category_expired_count, key=category_expired_count.get)
        count = category_expired_count[worst_category]
        if count >= 2:
            category_key = CATEGORY_KEY_MAP.get(worst_category, worst_category)
            category_display = t.get(category_key, worst_category)
            recommendations.append({
                "type": "habit",
                "message": t["rec_habit"].format(category=category_display, count=count)
            })

    if not recommendations:
        recommendations.append({
            "type": "good",
            "message": t["rec_good"]
        })

    return recommendations