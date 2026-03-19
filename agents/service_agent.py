"""
ServiceAgent - סוכן שירות לעסק הצמיגים
אחראי על: קביעת תורים, ניהול עבודות, ניתוב לנקודות שירות
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from agents.base_agent import BaseAgent

# Skills
try:
    from skills.route_calculator import (
        find_nearest_service_point,
        get_nearest_sorted,
        calculate_route,
        format_service_point,
        format_nearest_points,
        get_all_service_points,
    )
    from skills.whatsapp_sender import format_appointment_reminder, build_whatsapp_url
    _skills_ok = True
except ImportError:
    _skills_ok = False

APPOINTMENTS_FILE = Path(__file__).parent.parent / "data" / "appointments.json"
_appointments_lock = threading.Lock()

SYSTEM_PROMPT_FALLBACK = """אתה סוכן שירות של חברת יבוא צמיגים בישראל.
אתה מנהל תורים ומנתב לקוחות לנקודות שירות. דבר בנימוס ובמקצועיות, בעברית."""

# נקודות שירות בבעלות החברה
OWN_LOCATIONS = {
    "צפון": {
        "name": "סניף צפון - חיפה",
        "address": "רחוב התעשייה 12, חיפה",
        "phone": "04-8000001",
        "hours": "א-ה 08:00-18:00, ו 08:00-13:00",
    },
    "מרכז": {
        "name": "סניף מרכז - פתח תקווה",
        "address": "רחוב הרכב 7, פתח תקווה",
        "phone": "03-9000001",
        "hours": "א-ה 08:00-19:00, ו 08:00-14:00",
    },
}

EXTERNAL_PARTNERS_COUNT = 30

VALID_STATUSES = ("ממתין", "בביצוע", "הושלם", "בוטל")
SERVICE_TYPES = ("החלפת צמיגים", "עיצוב גלגלים", "תיקון פנצ'ר", "איזון ולחץ", "אחסון עונתי")


class ServiceAgent(BaseAgent):
    """סוכן שירות - תורים ונקודות שירות"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("service_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן שירות", system_prompt=system_prompt)
        APPOINTMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not APPOINTMENTS_FILE.exists():
            APPOINTMENTS_FILE.write_text("[]", encoding="utf-8")

    def run(self, user_input: str) -> str:
        return self.chat(user_input)

    # --- נקודות שירות ---

    def get_location_info(self, location_key: str) -> dict | None:
        """מחזיר פרטי נקודת שירות בבעלות"""
        return OWN_LOCATIONS.get(location_key)

    def list_own_locations(self) -> str:
        """מחזיר פרטי כל נקודות השירות בבעלות"""
        lines = ["נקודות שירות בבעלות החברה:"]
        for key, loc in OWN_LOCATIONS.items():
            lines.append(
                f"\n  {loc['name']}\n"
                f"  כתובת: {loc['address']}\n"
                f"  טלפון: {loc['phone']}\n"
                f"  שעות: {loc['hours']}"
            )
        lines.append(f"\nנוסף על כך: {EXTERNAL_PARTNERS_COUNT} נקודות שירות חיצוניות ברחבי הארץ.")
        return "\n".join(lines)

    # --- ניהול תורים ---

    def _load(self) -> list[dict]:
        with _appointments_lock:
            return json.loads(APPOINTMENTS_FILE.read_text(encoding="utf-8"))

    def _save(self, appointments: list[dict]):
        with _appointments_lock:
            APPOINTMENTS_FILE.write_text(
                json.dumps(appointments, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _next_id(self, appointments: list[dict]) -> int:
        return max((a["id"] for a in appointments), default=0) + 1

    def book_appointment(self, customer_name: str, phone: str, date: str,
                         time: str, location: str, service_type: str,
                         tire_size: str = "", notes: str = "") -> dict:
        """קובע תור חדש"""
        appointments = self._load()
        appt = {
            "id": self._next_id(appointments),
            "customer_name": customer_name,
            "phone": phone,
            "date": date,
            "time": time,
            "location": location,
            "service_type": service_type,
            "tire_size": tire_size,
            "notes": notes,
            "status": "ממתין",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        appointments.append(appt)
        self._save(appointments)
        return appt

    def list_appointments(self, date_filter: str = "", location_filter: str = "") -> list[dict]:
        """מחזיר תורים, עם סינון אופציונלי לפי תאריך ו/או מיקום"""
        appointments = self._load()
        if date_filter:
            appointments = [a for a in appointments if a["date"] == date_filter]
        if location_filter:
            appointments = [
                a for a in appointments
                if location_filter.lower() in a["location"].lower()
            ]
        return sorted(appointments, key=lambda a: (a["date"], a["time"]))

    def update_status(self, appt_id: int, new_status: str) -> bool:
        """מעדכן סטטוס עבודה"""
        if new_status not in VALID_STATUSES:
            return False
        appointments = self._load()
        for appt in appointments:
            if appt["id"] == appt_id:
                appt["status"] = new_status
                appt["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._save(appointments)
                return True
        return False

    def print_table(self, appointments: list[dict] | None = None) -> str:
        """מחזיר טבלת תורים כמחרוזת"""
        items = appointments if appointments is not None else self._load()
        if not items:
            return "אין תורים להצגה."

        header = f"{'#':<4} {'תאריך':<12} {'שעה':<7} {'לקוח':<18} {'טלפון':<14} {'מיקום':<10} {'שירות':<18} סטטוס"
        sep = "-" * 90
        rows = [header, sep]
        for a in items:
            rows.append(
                f"{a['id']:<4} {a['date']:<12} {a['time']:<7} {a['customer_name']:<18} "
                f"{a['phone']:<14} {a['location']:<10} {a['service_type']:<18} {a['status']}"
            )
        return "\n".join(rows)

    # --- Skills: מסלול ו-WhatsApp ---

    def find_nearest(self, address: str, service_type: str = "") -> str:
        """מוצא נקודת שירות קרובה לכתובת הלקוח"""
        if not _skills_ok:
            return self.list_own_locations()
        result = find_nearest_service_point(address, service_type)
        return format_service_point(result)

    def nearest_points_text(self, address: str, limit: int = 3) -> str:
        """טקסט מסודר של נקודות הקרובות ביותר"""
        if not _skills_ok:
            return self.list_own_locations()
        return format_nearest_points(address, limit)

    def route_info(self, origin: str, destination: str) -> str:
        """מרחק ומשך נסיעה משוערים"""
        if not _skills_ok:
            return "חישוב מסלול אינו זמין"
        info = calculate_route(origin, destination)
        if info.get("distance_km") is None:
            return info.get("note", "לא ניתן לחשב")
        return (
            f"מ-{info['origin']} אל {info['destination']}:\n"
            f"🛣 מרחק: {info['distance_km']} ק\"מ\n"
            f"⏱ זמן נסיעה משוער: {info['duration_min']} דקות\n"
            f"({info.get('note', '')})"
        )

    def whatsapp_reminder_url(self, phone: str, customer_name: str,
                               date: str, time: str, location: str,
                               service_type: str) -> str:
        """בונה URL לתזכורת WhatsApp ללקוח"""
        if not _skills_ok:
            return ""
        msg = format_appointment_reminder(customer_name, date, time, location, service_type)
        return build_whatsapp_url(phone, msg)

    def all_service_points_text(self) -> str:
        """רשימת כל נקודות השירות"""
        if not _skills_ok:
            return self.list_own_locations()
        points = get_all_service_points()
        own     = [p for p in points if p.get("type") == "own"]
        partner = [p for p in points if p.get("type") != "own"]
        lines   = [f"נקודות שירות ({len(points)} סה\"כ):", ""]
        lines.append(f"🏢 בבעלות החברה ({len(own)}):")
        for p in own:
            lines.append(f"  • {p['name']} | {p['address']} | {p['phone']}")
        lines.append(f"\n🤝 שותפים ({len(partner)}):")
        for p in partner:
            lines.append(f"  • {p['name']} | {p['address']} | {p['phone']}")
        return "\n".join(lines)

    def ai_schedule_advice(self, customer_need: str) -> str:
        """AI ייעוץ - מה הכי מתאים ללקוח"""
        locations_info = self.list_own_locations()
        prompt = (
            f"פרטי נקודות השירות:\n{locations_info}\n\n"
            f"צורך הלקוח: {customer_need}\n\n"
            "המלץ על נקודת השירות המתאימה, סוג העבודה וזמן משוער."
        )
        return self.chat(prompt, keep_history=False)
