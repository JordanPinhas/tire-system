"""
agents/rely_agent.py
סוכן מומחה למוצרי Rely® של Carpenter Co.
"""

from agents.base_agent import BaseAgent
from skills.rely_calculator import calculate_fill, search_size, get_all_sizes


class RelyAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="סוכן Rely",
            system_prompt=self.load_prompt("rely_agent.txt"),
        )

    def run(self, user_input: str) -> str:
        # טען נתוני מחירים ומלאי אמיתיים
        context = self._load_rely_context()
        enriched_input = f"{context}\n\nשאלת הלקוח: {user_input}"
        return self.chat(enriched_input, keep_history=False)

    def _load_rely_context(self) -> str:
        """טוען מחירים ומלאי Rely מהקבצים"""
        import json
        from pathlib import Path

        context_parts = []

        # טען מחירי Rely
        rely_file = Path(__file__).parent.parent / "data" / "rely_calculator.json"
        if rely_file.exists():
            data = json.loads(rely_file.read_text(encoding="utf-8"))
            context_parts.append(f"נתוני Rely:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

        # טען מלאי חביות
        inventory_file = Path(__file__).parent.parent / "data" / "inventory.json"
        if inventory_file.exists():
            inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
            rely_items = [
                item for item in inventory
                if "rely" in str(item).lower() or "t-25" in str(item).lower()
            ]
            if rely_items:
                context_parts.append(f"מלאי Rely:\n{json.dumps(rely_items, ensure_ascii=False, indent=2)}")

        if not context_parts:
            return "אין נתוני מחירים טעונים — השתמש בידע הכללי שלך על Rely T-25."

        return "\n\n".join(context_parts)

    def _format_result(self, r: dict) -> str:
        cost_line = f"• עלות כוללת: ₪{r['total_cost']:,.0f}" if r["total_cost"] else "• מחיר: לפי הסכמה"
        return (
            f"מידה: {r['tire_size']} | מוצר: {r['product_name']}\n"
            f"• ליטר לצמיג: {r['liters_per_tire']} ל׳  ({r['kg_per_tire']} ק״ג)\n"
            f"• מספר צמיגים: {r['num_tires']}\n"
            f"• סה״כ: {r['total_liters']} ליטר  ({r['total_kg']} ק״ג)\n"
            f"• חביות נדרשות: {r['barrels_needed']} × 200 ל׳\n"
            f"{cost_line}\n"
            f"• זמן אשפרה: {r['curing_time']}\n"
            f"⚠️  {r['notes']}"
        )
