"""
whatsapp_sender.py — שליחת הודעות WhatsApp
כרגע: פותח wa.me בדפדפן (ללא API בתשלום)
עתידי: אפשרות לחיבור ל-WhatsApp Business API
"""

import re
import urllib.parse
from datetime import datetime, timedelta

COMPANY_NAME  = "מערכת צמיגים AI"
COMPANY_PHONE = "04-8000001"
VAT_RATE      = 0.18


def send_whatsapp(phone: str, message: str) -> dict:
    """
    פותח WhatsApp Web עם הודעה מוכנה לשליחה.

    phone:   מספר ישראלי (050-..., 972..., וכו')
    message: תוכן ההודעה
    מחזיר:  {"ok": True, "url": str, "phone_intl": str}
    """
    phone_intl = _normalize_phone(phone)
    if not phone_intl:
        return {"ok": False, "error": f"מספר טלפון לא תקין: {phone}"}

    encoded = urllib.parse.quote(message, safe="")
    url     = f"https://wa.me/{phone_intl}?text={encoded}"

    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    return {
        "ok":         True,
        "url":        url,
        "phone_intl": phone_intl,
        "message":    message,
    }


def format_quote_message(
    customer_name: str,
    items: list,
    discount: float = 0,
    valid_days: int = 14,
    company_name: str = COMPANY_NAME,
    company_phone: str = COMPANY_PHONE,
) -> str:
    """
    מפרמט הצעת מחיר כהודעת WhatsApp מקצועית בעברית.

    items: [{"size", "brand", "qty", "unit_price"}]
    מחזיר מחרוזת מפורמטת עם bold (*)
    """
    valid_until = (datetime.now() + timedelta(days=valid_days)).strftime("%d/%m/%Y")

    lines = [
        f"*{company_name}* 🔵",
        f"📋 *הצעת מחיר — {customer_name}*",
        "",
        "━━━━━━━━━━━━━━━━",
    ]

    subtotal = 0.0
    for it in items:
        qty        = int(it.get("qty", 1))
        unit_price = float(it.get("unit_price", 0))
        total_item = qty * unit_price
        subtotal  += total_item
        size  = it.get("size", "")
        brand = it.get("brand", "")
        lines.append(f"🔹 {size} {brand}  ×{qty} = *{total_item:,.0f} ₪*".strip())

    lines.append("━━━━━━━━━━━━━━━━")

    if discount > 0:
        disc_amount = subtotal * discount / 100
        subtotal   -= disc_amount
        lines.append(f"🏷️ הנחה {discount:.0f}%: -*{disc_amount:,.0f} ₪*")

    vat   = subtotal * VAT_RATE
    final = subtotal + vat

    lines += [
        f'💰 סה"כ + מע"מ: *{final:,.0f} ₪*',
        "",
        f"📅 תוקף הצעה: {valid_until}",
        f"📞 לפרטים: {company_phone}",
        "",
        "_תודה על הפנייה! נשמח לעמוד לשירותכם_ 🙏",
    ]

    return "\n".join(lines)


def format_appointment_reminder(
    customer_name: str,
    date: str,
    time: str,
    location: str,
    service_type: str,
    company_phone: str = COMPANY_PHONE,
) -> str:
    """מפרמט הודעת תזכורת תור ב-WhatsApp"""
    return (
        f"שלום {customer_name} 👋\n\n"
        f"*תזכורת לתור*\n"
        f"📅 תאריך: *{date}*\n"
        f"⏰ שעה: *{time}*\n"
        f"📍 מיקום: {location}\n"
        f"🔧 שירות: {service_type}\n\n"
        f"לשינוי/ביטול: {company_phone}\n"
        f"_{COMPANY_NAME}_ 🔵"
    )


def format_general_message(
    customer_name: str,
    body: str,
    company_name: str = COMPANY_NAME,
    company_phone: str = COMPANY_PHONE,
) -> str:
    """מפרמט הודעה כללית"""
    return (
        f"שלום {customer_name},\n\n"
        f"{body}\n\n"
        f"📞 {company_phone}\n"
        f"_{company_name}_"
    )


def build_whatsapp_url(phone: str, message: str) -> str:
    """בונה URL ל-WhatsApp ללא פתיחת דפדפן"""
    phone_intl = _normalize_phone(phone)
    if not phone_intl:
        return ""
    return f"https://wa.me/{phone_intl}?text={urllib.parse.quote(message, safe='')}"


# ── עזר ────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """ממיר מספר ישראלי לפורמט בינלאומי 972XXXXXXXXX"""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)

    # כבר בינלאומי
    if digits.startswith("972") and 11 <= len(digits) <= 12:
        return digits

    # פורמט ישראלי 0XX-XXXXXXX (10 ספרות)
    if digits.startswith("0") and len(digits) == 10:
        return "972" + digits[1:]

    # 9 ספרות ללא אפס ראשוני
    if len(digits) == 9:
        return "972" + digits

    return ""
