"""
ReportingAgent - סוכן דוחות ואנליטיקה
אחראי על: דוח מלאי, דוח לידים, דוח תורים, סיכום יומי
"""

import json
from datetime import datetime, date
from pathlib import Path
from agents.base_agent import BaseAgent

DATA_DIR = Path(__file__).parent.parent / "data"
INVENTORY_FILE = DATA_DIR / "inventory.json"
LEADS_FILE = DATA_DIR / "leads.json"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"

SYSTEM_PROMPT_FALLBACK = """אתה סוכן דוחות ואנליטיקה של חברת יבוא צמיגים בישראל.
אתה מנתח נתוני עסק ומספק תובנות עסקיות ברורות. עברית עסקית-ניהולית."""


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


class ReportingAgent(BaseAgent):
    """סוכן דוחות - מנתח נתונים מכל קבצי ה-JSON ומגיש תובנות"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("reporting_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן דוחות", system_prompt=system_prompt)

    def run(self, user_input: str) -> str:
        # מעשיר בקשה חופשית עם סיכום נתונים
        context = self._build_full_context()
        prompt = f"נתוני העסק:\n{context}\n\nבקשה: {user_input}"
        return self.chat(prompt, keep_history=False)

    # --- בניית קונטקסט נתונים ---

    def _build_full_context(self) -> str:
        return "\n\n".join([
            self._inventory_context(),
            self._leads_context(),
            self._appointments_context(),
        ])

    def _inventory_context(self) -> str:
        inventory = _load_json(INVENTORY_FILE)
        if not inventory:
            return "מלאי: ריק."
        low_stock = [i for i in inventory if i["quantity"] < i.get("min_qty", 10)]
        total_value = sum(i["quantity"] * i["cost_price"] for i in inventory)
        lines = [
            f"מלאי ({len(inventory)} פריטים, שווי עלות: {total_value:,.0f}₪):",
            f"  פריטים במלאי נמוך: {len(low_stock)}",
        ]
        for item in inventory:
            flag = " [נמוך!]" if item["quantity"] < item.get("min_qty", 10) else ""
            lines.append(
                f"  #{item['id']} {item['brand']} {item['model']} {item['size']} "
                f"| {item['quantity']} יח'{flag}"
            )
        return "\n".join(lines)

    def _leads_context(self) -> str:
        leads = _load_json(LEADS_FILE)
        if not leads:
            return "לידים: אין."
        by_status: dict[str, int] = {}
        for lead in leads:
            s = lead.get("status", "לא ידוע")
            by_status[s] = by_status.get(s, 0) + 1
        lines = [f"לידים ({len(leads)} סה\"כ):"]
        for status, count in by_status.items():
            lines.append(f"  {status}: {count}")
        # לידים פתוחים ישנים (חדש)
        open_leads = [l for l in leads if l.get("status") == "חדש"]
        if open_leads:
            lines.append(f"  דורשים מעקב דחוף (חדש): {len(open_leads)}")
        return "\n".join(lines)

    def _appointments_context(self) -> str:
        appointments = _load_json(APPOINTMENTS_FILE)
        if not appointments:
            return "תורים: אין."
        today_str = date.today().strftime("%d/%m/%Y")
        by_status: dict[str, int] = {}
        for appt in appointments:
            s = appt.get("status", "לא ידוע")
            by_status[s] = by_status.get(s, 0) + 1
        today_appts = [a for a in appointments if a.get("date") == today_str]
        lines = [f"תורים ({len(appointments)} סה\"כ):"]
        for status, count in by_status.items():
            lines.append(f"  {status}: {count}")
        lines.append(f"  היום ({today_str}): {len(today_appts)}")
        return "\n".join(lines)

    # --- דוחות ספציפיים ---

    def inventory_report(self) -> str:
        """דוח מלאי מפורט עם ניתוח AI"""
        context = self._inventory_context()
        prompt = (
            f"{context}\n\n"
            "נתח את מצב המלאי:\n"
            "1. Executive summary (2 שורות)\n"
            "2. פריטים דורשים הזמנה דחופה\n"
            "3. פריטים שעשויים לעמוד זמן רב (עודף)\n"
            "4. שווי מלאי כולל ומשמעות עסקית\n"
            "5. 3 המלצות פעולה"
        )
        return self.chat(prompt, keep_history=False)

    def leads_report(self) -> str:
        """דוח לידים עם ניתוח המרה"""
        leads = _load_json(LEADS_FILE)
        context = self._leads_context()
        total = len(leads)
        closed = sum(1 for l in leads if l.get("status") == "סגור")
        lost = sum(1 for l in leads if l.get("status") == "אבוד")
        conversion = f"{(closed/total*100):.1f}%" if total else "0%"
        prompt = (
            f"{context}\n"
            f"סה\"כ לידים: {total} | נסגרו: {closed} | אבדו: {lost} | אחוז המרה: {conversion}\n\n"
            "נתח את מצב הלידים:\n"
            "1. Executive summary\n"
            "2. בעיות בצינור המכירות\n"
            "3. לידים שדורשים מעקב מיידי\n"
            "4. המלצות לשיפור אחוז ההמרה"
        )
        return self.chat(prompt, keep_history=False)

    def appointments_report(self, period: str = "היום") -> str:
        """דוח תורים לפי תקופה"""
        appointments = _load_json(APPOINTMENTS_FILE)
        context = self._appointments_context()

        # ספירת סוגי שירות
        service_counts: dict[str, int] = {}
        for appt in appointments:
            st = appt.get("service_type", "אחר")
            service_counts[st] = service_counts.get(st, 0) + 1

        services_text = "\n".join(f"  {s}: {c}" for s, c in service_counts.items())
        prompt = (
            f"{context}\n"
            f"פילוח לפי סוג עבודה:\n{services_text}\n\n"
            f"נתח תורים לתקופה: {period}\n"
            "1. Executive summary\n"
            "2. עומס לפי סניף\n"
            "3. סוגי עבודה נפוצים\n"
            "4. המלצות ייעול"
        )
        return self.chat(prompt, keep_history=False)

    def daily_report(self) -> str:
        """מייצר דוח יומי מלא על ידי שאילת כל הסוכנים"""

        # איסוף מידע מכל הסוכנים הרלוונטיים
        inventory_status = self.ask_agent(
            "סוכן מלאי",
            "תן לי סיכום קצר של מצב המלאי היום: כמה פריטים, מה במלאי נמוך, מה חסר"
        )
        leads_status = self.ask_agent(
            "סוכן מכירות",
            "תן לי סיכום סטטיסטי של הלידים: כמה חדשים, בטיפול, סגורים"
        )
        appointments_status = self.ask_agent(
            "סוכן שירות",
            "תן לי סיכום תורים להיום ולמחר: כמה תורים, באיזה סניפים"
        )
        pricing_alerts = self.ask_agent(
            "סוכן תמחור",
            "האם יש התראות תמחור חשובות היום? מוצרים שמחירם השתנה או חריגות"
        )

        # בניית הדוח המלא
        prompt = (
            f"בנה דוח יומי מנהלתי מקצועי בעברית:\n\n"
            f"📦 מלאי:\n{inventory_status}\n\n"
            f"👥 לידים ומכירות:\n{leads_status}\n\n"
            f"📅 תורים ושירות:\n{appointments_status}\n\n"
            f"💰 התראות תמחור:\n{pricing_alerts}\n\n"
            "סכם ב-3 נקודות פעולה עיקריות לסיום היום."
        )
        return self.chat(prompt, keep_history=False)

    def daily_summary(self) -> str:
        """סיכום יומי כולל של פעילות העסק"""
        today_str = date.today().strftime("%d/%m/%Y")
        context = self._build_full_context()
        prompt = (
            f"תאריך: {today_str}\n\n"
            f"נתוני העסק:\n{context}\n\n"
            "הכן סיכום יומי לבעל העסק:\n"
            "1. מצב כולל (תקין / דורש תשומת לב / דחוף)\n"
            "2. 3 הנושאים הדחופים ביותר להיום\n"
            "3. מלאי: התראות\n"
            "4. לידים: מה לטפל היום\n"
            "5. תורים: מה קורה היום\n"
            "6. המלצת פעולה #1 לבעל העסק לדקות הקרובות"
        )
        return self.chat(prompt, keep_history=False)
