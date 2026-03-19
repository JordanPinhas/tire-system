"""
InventoryAgent - סוכן מלאי לעסק הצמיגים
אחראי על: הצגת מלאי, עדכון כמויות, חיפוש לפי מידה, התראות מלאי נמוך
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from agents.base_agent import BaseAgent

INVENTORY_FILE = Path(__file__).parent.parent / "data" / "inventory.json"
_inventory_lock = threading.Lock()
LOW_STOCK_THRESHOLD = 10

SYSTEM_PROMPT_FALLBACK = """אתה סוכן מלאי של חברת יבוא צמיגים בישראל.
אתה מנהל מלאי, מחפש לפי מידה ומתריע על מלאי נמוך. עברית עסקית."""


class InventoryAgent(BaseAgent):
    """סוכן מלאי - ניהול מלאי צמיגים ב-JSON"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("inventory_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן מלאי", system_prompt=system_prompt)
        INVENTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not INVENTORY_FILE.exists():
            INVENTORY_FILE.write_text("[]", encoding="utf-8")

    def run(self, user_input: str) -> str:
        # מעשיר את הבקשה עם נתוני מלאי נוכחיים
        inventory = self._load()
        context = self._inventory_summary(inventory)
        prompt = f"מצב מלאי נוכחי:\n{context}\n\nשאלת המשתמש: {user_input}"
        return self.chat(prompt, keep_history=False)

    # --- CRUD מלאי ---

    def _load(self) -> list[dict]:
        with _inventory_lock:
            return json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))

    def _save(self, inventory: list[dict]):
        with _inventory_lock:
            INVENTORY_FILE.write_text(
                json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _next_id(self, inventory: list[dict]) -> int:
        return max((item["id"] for item in inventory), default=0) + 1

    def add_or_update(self, brand: str, model: str, size: str,
                      quantity: int, cost_price: float, min_qty: int = 10) -> dict:
        """מוסיף פריט חדש או מעדכן אם קיים (לפי brand+model+size)"""
        inventory = self._load()
        size_norm = size.upper().replace(" ", "")

        for item in inventory:
            if (item["brand"].lower() == brand.lower()
                    and item["model"].lower() == model.lower()
                    and item["size"].upper().replace(" ", "") == size_norm):
                item["quantity"] = quantity
                item["cost_price"] = cost_price
                item["min_qty"] = min_qty
                item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save(inventory)
                return item

        item = {
            "id": self._next_id(inventory),
            "brand": brand,
            "model": model,
            "size": size_norm,
            "quantity": quantity,
            "min_qty": min_qty,
            "cost_price": cost_price,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        inventory.append(item)
        self._save(inventory)
        return item

    def update_quantity(self, item_id: int, new_qty: int) -> bool:
        """מעדכן כמות לפי מזהה"""
        inventory = self._load()
        for item in inventory:
            if item["id"] == item_id:
                item["quantity"] = new_qty
                item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save(inventory)
                return True
        return False

    def find_by_size(self, size: str) -> list[dict]:
        """מחפש צמיגים לפי מידה (חלקי - 205/55R16 או רק 16)"""
        inventory = self._load()
        size_norm = size.upper().replace(" ", "")
        return [item for item in inventory if size_norm in item["size"]]

    def get_low_stock(self) -> list[dict]:
        """מחזיר פריטים מתחת לכמות המינימום"""
        inventory = self._load()
        return [item for item in inventory if item["quantity"] < item.get("min_qty", LOW_STOCK_THRESHOLD)]

    def list_all(self) -> list[dict]:
        return self._load()

    # --- תצוגה ---

    def _inventory_summary(self, inventory: list[dict]) -> str:
        if not inventory:
            return "המלאי ריק."
        lines = []
        for item in inventory:
            low = " [!מלאי נמוך]" if item["quantity"] < item.get("min_qty", LOW_STOCK_THRESHOLD) else ""
            lines.append(
                f"#{item['id']} {item['brand']} {item['model']} {item['size']} "
                f"| כמות: {item['quantity']}{low} | עלות: {item['cost_price']}₪"
            )
        return "\n".join(lines)

    def print_table(self, items: list[dict] | None = None) -> str:
        """מחזיר טבלת מלאי כמחרוזת טקסט"""
        inventory = items if items is not None else self._load()
        if not inventory:
            return "אין פריטים להצגה."

        header = f"{'#':<4} {'מותג':<12} {'דגם':<16} {'מידה':<12} {'כמות':<7} {'מינ.':<6} {'עלות':<8} סטטוס"
        sep = "-" * 70
        rows = [header, sep]
        for item in inventory:
            low_flag = "נמוך!" if item["quantity"] < item.get("min_qty", LOW_STOCK_THRESHOLD) else "תקין"
            rows.append(
                f"{item['id']:<4} {item['brand']:<12} {item['model']:<16} "
                f"{item['size']:<12} {item['quantity']:<7} {item.get('min_qty', LOW_STOCK_THRESHOLD):<6} "
                f"{item['cost_price']:<8.0f} {low_flag}"
            )
        return "\n".join(rows)
