"""
email_sender.py — שליחת מייל עם קובץ PDF מצורף (Gmail SMTP)
הגדרות ב-.env: GMAIL_USER, GMAIL_APP_PASSWORD
"""

import json
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

EMAIL_LOG_FILE = Path(__file__).parent.parent / "data" / "email_log.json"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587
COMPANY_NAME   = "מערכת צמיגים AI"
COMPANY_PHONE  = "04-8000001 | 03-9000001"


def send_quote_email(
    customer_email: str,
    customer_name: str,
    quote_pdf_path: str,
    message: str = "",
) -> dict:
    """
    שולח הצעת מחיר PDF למייל הלקוח.

    מחזיר: {"ok": bool, "message": str}
    """
    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_user or not gmail_pass:
        return {"ok": False, "message": "חסרים פרטי Gmail ב-.env (GMAIL_USER, GMAIL_APP_PASSWORD)"}

    if not customer_email or "@" not in customer_email:
        return {"ok": False, "message": "כתובת מייל לקוח לא תקינה"}

    pdf_path = Path(quote_pdf_path)
    if not pdf_path.exists():
        return {"ok": False, "message": f"קובץ PDF לא נמצא: {quote_pdf_path}"}

    # בנה הודעה
    msg            = MIMEMultipart()
    msg["From"]    = f"{COMPANY_NAME} <{gmail_user}>"
    msg["To"]      = customer_email
    msg["Subject"] = f"הצעת מחיר — {COMPANY_NAME}"

    body = message or (
        f"שלום {customer_name},\n\n"
        "מצורפת הצעת המחיר שהכנו עבורך.\n"
        "אנו עומדים לרשותך לכל שאלה או הבהרה.\n\n"
        f"בברכה,\n{COMPANY_NAME}\n"
        f"📞 {COMPANY_PHONE}"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # צרף PDF
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{pdf_path.name}"',
    )
    msg.attach(part)

    # שלח
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, customer_email, msg.as_bytes())

        _log(customer_email, customer_name, str(pdf_path), True, "")
        return {"ok": True, "message": f"✅ מייל נשלח בהצלחה ל-{customer_email}"}

    except smtplib.SMTPAuthenticationError:
        err = "שגיאת אימות Gmail — בדוק את GMAIL_APP_PASSWORD (השתמש ב-App Password, לא הסיסמה הרגילה)"
        _log(customer_email, customer_name, str(pdf_path), False, err)
        return {"ok": False, "message": err}

    except smtplib.SMTPRecipientsRefused:
        err = f"כתובת המייל נדחתה: {customer_email}"
        _log(customer_email, customer_name, str(pdf_path), False, err)
        return {"ok": False, "message": err}

    except Exception as e:
        err = str(e)
        _log(customer_email, customer_name, str(pdf_path), False, err)
        return {"ok": False, "message": f"שגיאה: {err}"}


def send_simple_email(to_email: str, subject: str, body: str) -> dict:
    """שליחת מייל פשוט ללא קובץ מצורף"""
    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_user or not gmail_pass:
        return {"ok": False, "message": "חסרים פרטי Gmail ב-.env"}

    msg            = MIMEMultipart()
    msg["From"]    = f"{COMPANY_NAME} <{gmail_user}>"
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_bytes())
        return {"ok": True, "message": f"מייל נשלח ל-{to_email}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def get_email_log(limit: int = 20) -> list:
    """מחזיר log של מיילים אחרונים"""
    try:
        if EMAIL_LOG_FILE.exists():
            log = json.loads(EMAIL_LOG_FILE.read_text(encoding="utf-8"))
            return log[-limit:]
    except Exception:
        pass
    return []


def _log(to: str, name: str, pdf: str, success: bool, error: str):
    """שמירת log"""
    try:
        EMAIL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = []
        if EMAIL_LOG_FILE.exists():
            log = json.loads(EMAIL_LOG_FILE.read_text(encoding="utf-8"))
        log.append({
            "sent_at":  datetime.now().isoformat(timespec="seconds"),
            "to_email": to,
            "to_name":  name,
            "pdf_file": pdf,
            "success":  success,
            "error":    error,
        })
        EMAIL_LOG_FILE.write_text(
            json.dumps(log[-100:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
