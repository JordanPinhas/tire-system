"""
skills/rely_calculator.py
חישובי מילוי Rely® לפי טבלת Carpenter הרשמית
מבנה חביות: חבית A (איזוציאנט) 1000L + חבית B (פוליאול) 1000L = סט מלא 2000L
"""

import json
from pathlib import Path

DATA_PATH  = Path(__file__).parent.parent / "data" / "rely_calculator.json"
STOCK_PATH = Path(__file__).parent.parent / "data" / "rely_stock.json"


def load_rely_data() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_stock() -> dict:
    if not STOCK_PATH.exists():
        default = {"T-25": {"A": 0, "B": 0}, "T-25-OEM": {"A": 0, "B": 0}}
        save_stock(default)
        return default
    with open(STOCK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # Migrate old flat format {"T-25": 0} → {"T-25": {"A": 0, "B": 0}}
    migrated = False
    for product in ["T-25", "T-25-OEM"]:
        if product in data and not isinstance(data[product], dict):
            data[product] = {"A": data[product], "B": data[product]}
            migrated = True
    if migrated:
        save_stock(data)
    return data


def save_stock(stock: dict):
    with open(STOCK_PATH, "w", encoding="utf-8") as f:
        json.dump(stock, f, ensure_ascii=False, indent=2)


def get_all_sizes() -> list[dict]:
    """מחזיר רשימת כל המידות עם הנתונים שלהן"""
    return load_rely_data()["tire_fills"]


def search_size(query: str) -> list[dict]:
    """חיפוש מידה חלקי"""
    data = load_rely_data()
    q = query.strip().lower()
    return [item for item in data["tire_fills"] if q in item["size"].lower()]


def calculate_fill(
    tire_size: str,
    num_tires: int = 1,
    product: str = "T-25",
    price_per_liter: float = 0.0,
) -> dict:
    """
    חישוב כמות חומר ועלות למילוי צמיגים.
    יחס ערבוב A:B = 1:1. כל חבית = 1000 ליטר. סט = חבית A + חבית B = 2000 ליטר.
    """
    data = load_rely_data()
    barrel_info = data.get("barrel_info", {})
    barrel_size = barrel_info.get("barrel_size_liters", 1000)
    set_total   = barrel_info.get("set_total_liters", 2000)

    # חיפוש מדויק (case-insensitive)
    match = None
    for item in data["tire_fills"]:
        if item["size"].lower() == tire_size.strip().lower():
            match = item
            break

    if not match:
        candidates = [
            item["size"] for item in data["tire_fills"]
            if tire_size.lower() in item["size"].lower()
        ]
        hint = f" — אולי התכוונת ל: {', '.join(candidates[:3])}" if candidates else ""
        return {"success": False, "error": f"מידה '{tire_size}' לא נמצאה בטבלה{hint}"}

    liters_per_tire = match["liters"]
    kg_per_tire     = match["kg"]
    total_liters    = round(liters_per_tire * num_tires, 1)
    total_kg        = round(kg_per_tire * num_tires, 1)
    total_cost      = round(total_liters * price_per_liter, 2) if price_per_liter else 0

    # חישוב A+B — יחס 1:1
    liters_a  = round(total_liters / 2, 1)
    liters_b  = round(total_liters / 2, 1)
    barrels_a = round(liters_a / barrel_size, 3)
    barrels_b = round(liters_b / barrel_size, 3)
    sets_needed = round(total_liters / set_total, 3)

    prod_info = data["products"].get(product, {})

    return {
        "success":           True,
        "tire_size":         match["size"],
        "num_tires":         num_tires,
        "product":           product,
        "product_name":      prod_info.get("name", product),
        "liters_per_tire":   liters_per_tire,
        "kg_per_tire":       kg_per_tire,
        "total_liters":      total_liters,
        "total_kg":          total_kg,
        "liters_component_a": liters_a,
        "liters_component_b": liters_b,
        "barrels_a":         barrels_a,
        "barrels_b":         barrels_b,
        "sets_needed":       sets_needed,
        "barrel_note":       "כל סט = חבית A (1000L) + חבית B (1000L)",
        "total_cost":        total_cost,
        "curing_time":       "24–48 שעות",
        "notes":             "יש להסיר שסתום אוויר לפני מילוי",
    }


def get_stock_status() -> dict:
    """מחזיר מלאי חביות A+B עם סטים זמינים והתראות"""
    LOW_THRESHOLD = 2
    stock = load_stock()
    result = {}
    for product in ["T-25", "T-25-OEM"]:
        prod = stock.get(product, {"A": 0, "B": 0})
        a = prod.get("A", 0)
        b = prod.get("B", 0)
        result[product] = {
            "A":        a,
            "B":        b,
            "sets":     min(a, b),
            "low_a":    a < LOW_THRESHOLD,
            "low_b":    b < LOW_THRESHOLD,
            "imbalance": a != b,
        }
    return result


def update_stock(product: str, component: str, delta: float) -> dict:
    """מוסיף/מוריד חביות מהמלאי. component = 'A' או 'B'. delta יכול להיות שברי (0.5)."""
    stock = load_stock()
    if product not in stock:
        return {"success": False, "error": f"מוצר לא ידוע: {product}"}
    if component not in ("A", "B"):
        return {"success": False, "error": f"רכיב לא ידוע: {component} (צפוי A או B)"}
    stock[product][component] = max(0, round(stock[product][component] + delta, 2))
    save_stock(stock)
    return {"success": True, "product": product, "component": component,
            "quantity": stock[product][component]}
