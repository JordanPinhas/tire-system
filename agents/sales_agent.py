"""
SalesAgent - סוכן מכירות לעסק הצמיגים
אחראי על: הצעות מחיר, ניהול לידים, ייעוץ מכירות
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from agents.base_agent import BaseAgent

# Skills
try:
    from skills.pdf_quote import create_quote_pdf, format_quote_for_chat
    from skills.email_sender import send_quote_email
    from skills.whatsapp_sender import (
        format_quote_message, send_whatsapp, build_whatsapp_url,
    )
    _skills_ok = True
except ImportError:
    _skills_ok = False

LEADS_FILE = Path(__file__).parent.parent / "data" / "leads.json"
_leads_lock = threading.Lock()

SYSTEM_PROMPT_FALLBACK = """אתה סוכן מכירות בכיר של חברת יבוא וסיטונאות צמיגים בישראל.
אתה בונה הצעות מחיר, מנהל לידים ומייעץ על אסטרטגיית מכירה.
דבר בטון מקצועי ואמין, בעברית עסקית."""

CUSTOMER_TYPES = {
    "פרטי": "לקוח פרטי",
    "מוסך": "מוסך / צמיגייה",
    "ציי": "ציי רכב / חברה",
    "קמעונאי": "קמעונאי / מפיץ",
}


class SalesAgent(BaseAgent):
    """סוכן מכירות - הצעות מחיר וניהול לידים"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("sales_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן מכירות", system_prompt=system_prompt)
        LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not LEADS_FILE.exists():
            LEADS_FILE.write_text("[]", encoding="utf-8")

    def run(self, user_input: str) -> str:
        return self.chat(user_input)

    def create_quote(self, customer_type: str, products: str, quantity: int, notes: str = "") -> str:
        """יוצר הצעת מחיר מותאמת לסוג הלקוח"""
        customer_label = CUSTOMER_TYPES.get(customer_type, customer_type)

        inventory_info = self.ask_agent("סוכן מלאי", f"האם יש במלאי: {products}?")
        pricing_info   = self.ask_agent("סוכן תמחור", f"מחיר מומלץ ל-{products} ללקוח {customer_label}, כמות {quantity}")

        prompt = (
            f"בנה הצעת מחיר מקצועית עבור:\n"
            f"סוג לקוח: {customer_label}\n"
            f"מוצרים: {products}\n"
            f"כמות: {quantity} יחידות\n"
            f"\n--- נתוני מלאי (סוכן מלאי) ---\n{inventory_info}\n"
            f"\n--- המלצת תמחור (סוכן תמחור) ---\n{pricing_info}\n"
        )
        if notes:
            prompt += f"הערות: {notes}\n"
        prompt += (
            "\nכלול בהצעה:\n"
            "1. כותרת + תאריך + תוקף ההצעה\n"
            "2. פירוט המוצרים (מפרט + מחיר יחידה + סה\"כ)\n"
            "3. תנאי תשלום ואספקה מתאימים לסוג הלקוח\n"
            "4. הנחת כמות אם רלוונטי\n"
            "5. קריאה לפעולה וסגירה"
        )
        return self.chat(prompt, keep_history=False)

    def create_fleet_quote(self, company: str, vehicles: int, tire_type: str, annual_est: int) -> str:
        """יוצר הצעת מחיר לציי רכב - חוזה שנתי"""
        inventory_info = self.ask_agent(
            "סוכן מלאי",
            f"האם יש במלאי: {tire_type}? מה הכמות הזמינה לציי רכב גדול?"
        )
        pricing_info = self.ask_agent(
            "סוכן תמחור",
            f"מחיר מומלץ ל-{tire_type} ללקוח ציי רכב, כמות שנתית {annual_est} יחידות"
        )
        prompt = (
            f"בנה הצעת מחיר לחוזה שנתי עבור ציי רכב:\n"
            f"חברה: {company}\n"
            f"מספר רכבים: {vehicles}\n"
            f"סוג צמיגים: {tire_type}\n"
            f"הערכת צריכה שנתית: {annual_est} יחידות\n\n"
            f"\nמידע ממלאי:\n{inventory_info}\n"
            f"\nמידע תמחור:\n{pricing_info}\n\n"
            "כלול: מחיר סיטונאי, תנאי חוזה שנתי, SLA אספקה, "
            "הנחת נאמנות, ותנאי תשלום (60/90 יום)."
        )
        return self.chat(prompt, keep_history=False)

    # --- ניהול לידים ---

    def _load_leads(self) -> list[dict]:
        with _leads_lock:
            return json.loads(LEADS_FILE.read_text(encoding="utf-8"))

    def _save_leads(self, leads: list[dict]):
        with _leads_lock:
            LEADS_FILE.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_lead(self, name: str, phone: str, customer_type: str,
                 interest: str, notes: str = "") -> dict:
        """מוסיף ליד חדש ל-leads.json"""
        leads = self._load_leads()
        lead = {
            "id": max((l["id"] for l in leads), default=0) + 1,
            "name": name,
            "phone": phone,
            "customer_type": customer_type,
            "interest": interest,
            "notes": notes,
            "status": "חדש",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        leads.append(lead)
        self._save_leads(leads)
        return lead

    def list_leads(self, status_filter: str = "") -> list[dict]:
        """מחזיר רשימת לידים, עם סינון אופציונלי לפי סטטוס"""
        leads = self._load_leads()
        if status_filter:
            leads = [l for l in leads if l.get("status") == status_filter]
        return leads

    def update_lead_status(self, lead_id: int, new_status: str) -> bool:
        """מעדכן סטטוס ליד (חדש / בטיפול / סגור / אבוד)"""
        leads = self._load_leads()
        for lead in leads:
            if lead["id"] == lead_id:
                lead["status"] = new_status
                lead["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save_leads(leads)
                return True
        return False

    # --- Skills: PDF / מייל / WhatsApp ---

    def create_pdf_quote(
        self,
        customer: dict,
        items: list,
        discount: float = 0,
        valid_days: int = 14,
    ) -> str:
        """יוצר PDF הצעת מחיר ומחזיר נתיב לקובץ"""
        if not _skills_ok:
            return "skills לא זמינים — נא להתקין reportlab"
        try:
            pdf_path = create_quote_pdf(customer, items, discount, valid_days)
            return pdf_path
        except Exception as e:
            return f"שגיאה ביצירת PDF: {e}"

    def email_quote(
        self,
        customer_email: str,
        customer_name: str,
        pdf_path: str,
        message: str = "",
    ) -> dict:
        """שולח הצעת מחיר במייל"""
        if not _skills_ok:
            return {"ok": False, "message": "skills לא זמינים"}
        return send_quote_email(customer_email, customer_name, pdf_path, message)

    def whatsapp_quote_url(
        self,
        phone: str,
        customer_name: str,
        items: list,
        discount: float = 0,
    ) -> str:
        """בונה URL לשליחת הצעת מחיר ב-WhatsApp"""
        if not _skills_ok:
            return ""
        msg = format_quote_message(customer_name, items, discount)
        return build_whatsapp_url(phone, msg)

    def get_lead_summary(self) -> str:
        """מחזיר סיכום סטטיסטי של הלידים"""
        leads = self._load_leads()
        if not leads:
            return "אין לידים במערכת."

        by_status: dict[str, int] = {}
        for lead in leads:
            s = lead.get("status", "לא ידוע")
            by_status[s] = by_status.get(s, 0) + 1

        lines = [f"סה\"כ לידים: {len(leads)}"]
        for status, count in by_status.items():
            lines.append(f"  {status}: {count}")
        return "\n".join(lines)
