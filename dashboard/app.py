"""
דשבורד מנהל - מערכת צמיגים
Flask web dashboard for the tire business AI system
"""

import sys
import json
import importlib
import os
import functools
from datetime import date, datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, session

# מאפשר ייבוא agents/ ו-skills/ מהספרייה האם
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

app = Flask(__name__)

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
SESSION_SECRET     = os.getenv("SESSION_SECRET", "change-me-in-production")
API_KEY            = os.getenv("API_KEY", "")
app.secret_key     = SESSION_SECRET


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def require_api_key(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not API_KEY or key != API_KEY:
            return jsonify({"error": "API Key שגוי"}), 401
        return f(*args, **kwargs)
    return decorated


@app.before_request
def check_auth():
    """הגן על כל הדשבורד — פרט לנתיבים ציבוריים"""
    public = {"/login", "/logout", "/health", "/widget"}
    if (not session.get("logged_in")
            and request.path not in public
            and not request.path.startswith("/api/v1/")
            and not request.path.startswith("/api/widget/")):
        return redirect("/login")

# --- מיפוי סוכנים לצ'אט ---
CHAT_AGENTS = {
    "סוכן שיווק":       ("agents.marketing_agent",   "MarketingAgent",   "📢"),
    "סוכן קופירייטינג": ("agents.copywriting_agent", "CopywritingAgent", "✍️"),
    "סוכן מכירות":      ("agents.sales_agent",        "SalesAgent",       "💼"),
    "סוכן מלאי":        ("agents.inventory_agent",    "InventoryAgent",   "📦"),
    "סוכן שירות":       ("agents.service_agent",      "ServiceAgent",     "🔧"),
    "סוכן תמחור":       ("agents.pricing_agent",      "PricingAgent",     "💰"),
    "סוכן תמיכה":       ("agents.support_agent",      "SupportAgent",     "💬"),
    "סוכן דוחות":       ("agents.reporting_agent",    "ReportingAgent",   "📊"),
}

# סינגלטונים של סוכנים (נשמרים כל עוד השרת רץ)
_agent_instances: dict = {}

# Orchestrator singleton — נטען בפעם הראשונה שנדרש
_orchestrator_instance = None

def get_orchestrator():
    """מחזיר Orchestrator יחיד עם כל הסוכנים מחוברים"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from orchestrator.orchestrator import Orchestrator
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance

def get_agent(name: str):
    """מחזיר סוכן קיים או יוצר חדש"""
    if name not in CHAT_AGENTS:
        return None
    if name not in _agent_instances:
        module_path, class_name, _ = CHAT_AGENTS[name]
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            _agent_instances[name] = cls()
        except Exception:
            return None
    return _agent_instances[name]

DATA_DIR = Path(__file__).parent.parent / "data"
INVENTORY_FILE = DATA_DIR / "inventory.json"
LEADS_FILE = DATA_DIR / "leads.json"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"
IMPORT_LOG_FILE = DATA_DIR / "import_log.json"
REPORTS_HISTORY_FILE = DATA_DIR / "reports_history.json"
CAMPAIGNS_QUEUE_FILE = DATA_DIR / "campaigns_queue.json"
CAMPAIGNS_LOG_FILE   = DATA_DIR / "campaigns_log.json"

# תיקיית העלאות זמניות
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

AGENTS_COUNT = 8

AGENT_ICONS = {
    "סוכן שיווק":       ("📢", "פרסומות וקמפיינים"),
    "סוכן קופירייטינג": ("✍️", "תיאורי מוצר ומודעות"),
    "סוכן מכירות":      ("💼", "הצעות מחיר ולידים"),
    "סוכן מלאי":        ("📦", "ניהול מלאי צמיגים"),
    "סוכן שירות":       ("🔧", "תורים ונקודות שירות"),
    "סוכן תמחור":       ("💰", "תמחור ומרג'ין"),
    "סוכן תמיכה":       ("💬", "ייעוץ לקוחות וFAQ"),
    "סוכן דוחות":       ("📊", "דוחות ואנליטיקה"),
    "סוכן Rely":        ("🛡️", "מילוי פוליאוריתן Rely®"),
}


def save_report_to_history(report_text: str) -> dict:
    """שומר דוח להיסטוריה ומחזיר את הרשומה"""
    try:
        history = json.loads(REPORTS_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        history = []
    record = {
        "id": len(history) + 1,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "time": datetime.now().strftime("%H:%M"),
        "datetime": datetime.now().isoformat(),
        "preview": report_text[:200],
        "content": report_text,
    }
    history.insert(0, record)
    history = history[:30]
    REPORTS_HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record


def _load_campaigns_queue():
    try:
        return json.loads(CAMPAIGNS_QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_campaigns_queue(queue):
    CAMPAIGNS_QUEUE_FILE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def _load_campaigns_log():
    try:
        return json.loads(CAMPAIGNS_LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_campaigns_log(log):
    CAMPAIGNS_LOG_FILE.write_text(
        json.dumps(log, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _build_report_pdf(report_text: str, report_date: str):
    """מייצר PDF מתוכן דוח ומחזיר BytesIO מוכן לשליחה"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors
    from io import BytesIO
    import re

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=12, alignment=1,
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontSize=11, leading=16, spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#2c3e50'),
        spaceBefore=12, spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=9, textColor=colors.grey, alignment=1,
    )

    story.append(Paragraph(f"דוח יומי מנהלתי | {report_date}", title_style))
    story.append(Spacer(1, 0.5*cm))

    for line in report_text.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.3*cm))
            continue
        line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        line = re.sub(r'#{1,3}\s*', '', line)
        line = re.sub(r'[`]', '', line)
        if line.startswith('#'):
            story.append(Paragraph(line, heading_style))
        else:
            story.append(Paragraph(line, body_style))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"הופק אוטומטית על ידי מערכת AI צמיגים | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        footer_style
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer


# --- נתוני דמו ---

DEMO_INVENTORY = [
    {"id": 1, "brand": "Michelin", "model": "Primacy 4", "size": "205/55R16", "quantity": 24, "min_qty": 10, "cost_price": 380, "sell_price": 520},
    {"id": 2, "brand": "Bridgestone", "model": "Turanza T005", "size": "225/45R17", "quantity": 7, "min_qty": 10, "cost_price": 420, "sell_price": 580},
    {"id": 3, "brand": "Continental", "model": "EcoContact 6", "size": "195/65R15", "quantity": 3, "min_qty": 10, "cost_price": 310, "sell_price": 440},
    {"id": 4, "brand": "Pirelli", "model": "Cinturato P7", "size": "245/40R18", "quantity": 18, "min_qty": 8, "cost_price": 510, "sell_price": 720},
    {"id": 5, "brand": "Goodyear", "model": "EfficientGrip", "size": "215/60R16", "quantity": 5, "min_qty": 10, "cost_price": 340, "sell_price": 480},
    {"id": 6, "brand": "Hankook", "model": "Kinergy Eco2", "size": "185/65R15", "quantity": 32, "min_qty": 12, "cost_price": 220, "sell_price": 310},
    {"id": 7, "brand": "Michelin", "model": "CrossClimate 2", "size": "205/60R16", "quantity": 11, "min_qty": 10, "cost_price": 450, "sell_price": 630},
    {"id": 8, "brand": "Yokohama", "model": "BluEarth-A", "size": "225/50R17", "quantity": 2, "min_qty": 8, "cost_price": 390, "sell_price": 540},
]

DEMO_LEADS = [
    {"id": 1, "name": "דוד לוי", "phone": "050-1234567", "customer_type": "מוסך", "interest": "צמיגי קיץ 205/55R16 x20 יח'", "notes": "", "status": "חדש", "created_at": "2026-03-10T09:15:00"},
    {"id": 2, "name": "רחל כהן", "phone": "052-9876543", "customer_type": "פרטי", "interest": "החלפת 4 צמיגים לאוונסיס", "notes": "מגיעה שישי", "status": "בטיפול", "created_at": "2026-03-11T11:30:00"},
    {"id": 3, "name": "אמיר גולן", "phone": "054-5551234", "customer_type": "ציי", "interest": "חוזה שנתי 80 רכבים - 18 אינץ'", "notes": "בקש הצעת מחיר דחוף", "status": "חדש", "created_at": "2026-03-12T08:45:00"},
    {"id": 4, "name": "צמיגי השרון בע\"מ", "phone": "09-7654321", "customer_type": "קמעונאי", "interest": "Michelin Primacy 4 - 50 יח' לחודש", "notes": "", "status": "סגור", "created_at": "2026-03-01T14:00:00"},
    {"id": 5, "name": "יעל ברק", "phone": "053-3334455", "customer_type": "פרטי", "interest": "צמיגי חורף לגולן", "notes": "", "status": "אבוד", "created_at": "2026-03-05T16:20:00"},
    {"id": 6, "name": "מוסך אבי מוטורס", "phone": "03-6667788", "customer_type": "מוסך", "interest": "Bridgestone Turanza - 15 יח'", "notes": "אשראי 30 יום", "status": "בטיפול", "created_at": "2026-03-13T10:00:00"},
    {"id": 7, "name": "חברת משלוחים מהיר", "phone": "072-5554433", "customer_type": "ציי", "interest": "195/65R15 x100 יח' לשנה", "notes": "פגישה נקבעה", "status": "בטיפול", "created_at": "2026-03-09T13:15:00"},
    {"id": 8, "name": "נועם שמיר", "phone": "058-2223344", "customer_type": "פרטי", "interest": "4 צמיגים לסובארו פורסטר", "notes": "", "status": "חדש", "created_at": "2026-03-13T09:30:00"},
]

DEMO_APPOINTMENTS = [
    {"id": 1, "customer_name": "דוד לוי", "phone": "050-1234567", "date": "13/03/2026", "time": "09:00", "location": "מרכז", "service_type": "החלפת צמיגים", "tire_size": "205/55R16", "notes": "", "status": "בביצוע"},
    {"id": 2, "customer_name": "שרה אברהם", "phone": "052-6667788", "date": "13/03/2026", "time": "11:30", "location": "צפון", "service_type": "איזון ולחץ", "tire_size": "", "notes": "", "status": "ממתין"},
    {"id": 3, "customer_name": "מוסך אבי", "phone": "03-6667788", "date": "13/03/2026", "time": "14:00", "location": "מרכז", "service_type": "עיצוב גלגלים", "tire_size": "225/45R17", "notes": "15 יחידות", "status": "ממתין"},
    {"id": 4, "customer_name": "יוסי כהן", "phone": "054-1112233", "date": "14/03/2026", "time": "08:30", "location": "צפון", "service_type": "החלפת צמיגים", "tire_size": "195/65R15", "notes": "", "status": "ממתין"},
    {"id": 5, "customer_name": "רינה גרינברג", "phone": "050-9998877", "date": "14/03/2026", "time": "10:00", "location": "מרכז", "service_type": "תיקון פנצ'ר", "tire_size": "", "notes": "", "status": "ממתין"},
    {"id": 6, "customer_name": "מנחם רוזן", "phone": "053-4445566", "date": "12/03/2026", "time": "15:00", "location": "מרכז", "service_type": "אחסון עונתי", "tire_size": "", "notes": "", "status": "הושלם"},
]

# --- טעינת נתונים ---

def load_json(path: Path, demo_data: list) -> list:
    """טוען JSON. מחזיר דמו רק אם הקובץ לא קיים (רשימה ריקה = מלאי נוקה)."""
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return demo_data

def save_json(path: Path, data: list):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_inventory() -> list:
    result = load_json(INVENTORY_FILE, DEMO_INVENTORY)
    # DEBUG — remove after diagnosis
    src = "REAL" if INVENTORY_FILE.exists() and result is not DEMO_INVENTORY else "DEMO"
    print(f"[get_inventory] source={src}  count={len(result)}  path={INVENTORY_FILE.resolve()}")
    return result

def get_leads() -> list:
    return load_json(LEADS_FILE, DEMO_LEADS)

def get_appointments() -> list:
    return load_json(APPOINTMENTS_FILE, DEMO_APPOINTMENTS)

def get_import_log() -> list:
    try:
        if IMPORT_LOG_FILE.exists():
            return json.loads(IMPORT_LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return []

# --- חישובים ---

def calc_summary() -> dict:
    inventory = get_inventory()
    leads = get_leads()
    appointments = get_appointments()
    today = date.today().strftime("%d/%m/%Y")

    low_stock = [i for i in inventory if i["quantity"] < i.get("min_qty", 10)]
    open_leads = [l for l in leads if l.get("status") in ("חדש", "בטיפול")]
    today_appts = [a for a in appointments if a.get("date") == today]
    total_inventory_value = sum(i["quantity"] * i["cost_price"] for i in inventory)
    closed_leads = [l for l in leads if l.get("status") == "סגור"]
    conversion = round(len(closed_leads) / len(leads) * 100) if leads else 0

    return {
        "inventory_count": len(inventory),
        "low_stock_count": len(low_stock),
        "open_leads_count": len(open_leads),
        "today_appointments": len(today_appts),
        "agents_active": len(get_orchestrator().agents),
        "total_inventory_value": total_inventory_value,
        "leads_total": len(leads),
        "conversion_pct": conversion,
    }

# --- נתיבים ראשיים ---

@app.route("/")
def index():
    summary = calc_summary()
    leads = get_leads()
    appointments = get_appointments()
    today = date.today().strftime("%d/%m/%Y")

    recent_leads = sorted(leads, key=lambda l: l.get("created_at", ""), reverse=True)[:5]
    upcoming = [a for a in appointments if a.get("status") in ("ממתין", "בביצוע")]
    upcoming = sorted(upcoming, key=lambda a: (a.get("date", ""), a.get("time", "")))[:6]

    orch = get_orchestrator()
    agents_list = [
        {"name": name, "icon": AGENT_ICONS.get(name, ("🤖", ""))[0],
         "desc": AGENT_ICONS.get(name, ("🤖", ""))[1]}
        for name in orch.agents
    ]
    return render_template("index.html",
                           summary=summary,
                           recent_leads=recent_leads,
                           upcoming=upcoming,
                           today=today,
                           agents_count=len(orch.agents),
                           agents=agents_list)

@app.route("/inventory")
def inventory():
    items = get_inventory()
    low_ids = {i["id"] for i in items if i["quantity"] < i.get("min_qty", 10)}
    total_value = sum(i["quantity"] * i["cost_price"] for i in items)
    total_sell_value = sum(i["quantity"] * i.get("sell_price", 0) for i in items)
    low_count = len(low_ids)
    import_log = get_import_log()
    brands = sorted(set(i["brand"] for i in items))
    sizes  = sorted(set(i["size"]  for i in items))
    return render_template("inventory.html",
                           items=items,
                           low_ids=low_ids,
                           total_value=total_value,
                           total_sell_value=total_sell_value,
                           low_count=low_count,
                           import_log=import_log,
                           brands=brands,
                           sizes=sizes)

@app.route("/leads")
def leads():
    all_leads = get_leads()
    status_filter = request.args.get("status", "")
    if status_filter:
        filtered = [l for l in all_leads if l.get("status") == status_filter]
    else:
        filtered = all_leads

    status_counts = {}
    for l in all_leads:
        s = l.get("status", "לא ידוע")
        status_counts[s] = status_counts.get(s, 0) + 1

    return render_template("leads.html",
                           leads=filtered,
                           all_count=len(all_leads),
                           status_counts=status_counts,
                           active_filter=status_filter)

@app.route("/appointments")
def appointments():
    all_appts = get_appointments()
    today = date.today().strftime("%d/%m/%Y")
    location_filter = request.args.get("location", "")
    if location_filter:
        filtered = [a for a in all_appts if a.get("location") == location_filter]
    else:
        filtered = all_appts
    filtered = sorted(filtered, key=lambda a: (a.get("date", ""), a.get("time", "")))

    today_count = len([a for a in all_appts if a.get("date") == today])
    pending_count = len([a for a in all_appts if a.get("status") == "ממתין"])

    return render_template("appointments.html",
                           appointments=filtered,
                           today=today,
                           today_count=today_count,
                           pending_count=pending_count,
                           active_location=location_filter)

# --- API כללי ---

@app.route("/api/summary")
def api_summary():
    return jsonify(calc_summary())

@app.route("/api/leads/<int:lead_id>/status", methods=["POST"])
def update_lead_status(lead_id):
    new_status = request.form.get("status", "").strip()
    valid = ("חדש", "בטיפול", "סגור", "אבוד")
    if new_status not in valid:
        return jsonify({"error": "סטטוס לא תקין"}), 400

    leads = get_leads()
    updated = False
    for lead in leads:
        if lead["id"] == lead_id:
            lead["status"] = new_status
            lead["updated_at"] = datetime.now().isoformat(timespec="seconds")
            updated = True
            break

    if updated:
        if LEADS_FILE.exists() and json.loads(LEADS_FILE.read_text(encoding="utf-8")):
            save_json(LEADS_FILE, leads)

    return redirect(url_for("leads"))

# --- API מלאי ---

@app.route("/inventory/add", methods=["POST"])
def inventory_add():
    """הוספה ידנית של פריט מלאי"""
    data = request.get_json(silent=True) or {}
    size = data.get("size", "").strip()
    if not size:
        return jsonify({"error": "מידה היא שדה חובה"}), 400

    items = get_inventory()
    next_id = max((i.get("id", 0) for i in items), default=0) + 1

    new_item = {
        "id":         next_id,
        "brand":      data.get("brand", "לא ידוע").strip(),
        "model":      data.get("model", "").strip(),
        "tire_model": data.get("tire_model", "").strip(),
        "size":       size,
        "quantity":   int(data.get("quantity", 0)),
        "cost_price": float(data.get("cost_price", 0)),
        "sell_price": float(data.get("sell_price", 0)),
        "min_qty":    int(data.get("min_qty", 10)),
    }
    items.append(new_item)
    save_json(INVENTORY_FILE, items)
    return jsonify({"ok": True, "item": new_item})


@app.route("/inventory/update", methods=["POST"])
def inventory_update():
    """עדכון פריט קיים"""
    data = request.get_json(silent=True) or {}
    item_id = data.get("id")
    if item_id is None:
        return jsonify({"error": "id חסר"}), 400

    items = get_inventory()
    updated = False
    for item in items:
        if item.get("id") == int(item_id):
            for field in ("brand", "model", "tire_model", "size", "quantity", "cost_price", "sell_price", "min_qty"):
                if field in data:
                    val = data[field]
                    if field in ("quantity", "min_qty"):
                        item[field] = int(val)
                    elif field in ("cost_price", "sell_price"):
                        item[field] = float(val)
                    else:
                        item[field] = str(val).strip() if val is not None else ""
            updated = True
            break

    if not updated:
        return jsonify({"error": "פריט לא נמצא"}), 404

    save_json(INVENTORY_FILE, items)
    return jsonify({"ok": True})


@app.route("/inventory/clear", methods=["POST"])
def inventory_clear():
    """מוחק את כל המלאי ומאתחל לרשימה ריקה"""
    save_json(INVENTORY_FILE, [])
    return jsonify({"ok": True})


@app.route("/inventory/delete/<int:item_id>", methods=["POST"])
def inventory_delete(item_id):
    """מחיקת פריט"""
    items = get_inventory()
    original_len = len(items)
    items = [i for i in items if i.get("id") != item_id]
    if len(items) == original_len:
        return jsonify({"error": "פריט לא נמצא"}), 404
    save_json(INVENTORY_FILE, items)
    return jsonify({"ok": True})


def _parse_file(file_path: str, source: str, use_ai: bool = False) -> tuple[list[dict], str]:
    """
    רק פרסור קובץ — ללא שמירה לדיסק.
    מחזיר (items, raw_text_snippet).
    השמירה בפועל מתבצעת רק דרך /inventory/import/confirm.
    """
    from skills.inventory_import import (
        import_from_excel, import_from_pdf, import_from_image,
        import_from_linglong_pdf, extract_pdf_raw_text,
    )

    ext = Path(file_path).suffix.lower()
    raw_text = ""

    if source == "linglong":
        raw_text = extract_pdf_raw_text(file_path)
        new_items = import_from_linglong_pdf(file_path)
    elif source == "excel" or ext in (".xlsx", ".xls", ".csv"):
        new_items = import_from_excel(file_path)
    elif source == "pdf" or ext == ".pdf":
        raw_text = extract_pdf_raw_text(file_path)
        new_items = import_from_pdf(file_path)
    elif source == "image" or ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        new_items = import_from_image(file_path)
    else:
        return None, "סוג קובץ לא נתמך"

    # אם לא זוהו פריטים — נסה AI fallback
    if not new_items and use_ai and raw_text:
        from skills.inventory_import import ai_extract
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        try:
            new_items = ai_extract(raw_text, client)
        except Exception:
            pass

    return new_items, raw_text


@app.route("/inventory/import/excel", methods=["POST"])
def inventory_import_excel():
    return _handle_file_upload("excel")

@app.route("/inventory/import/pdf", methods=["POST"])
def inventory_import_pdf():
    return _handle_file_upload("pdf")

@app.route("/inventory/import/image", methods=["POST"])
def inventory_import_image():
    return _handle_file_upload("image")

@app.route("/inventory/import/linglong", methods=["POST"])
def inventory_import_linglong():
    return _handle_file_upload("linglong")


def _handle_file_upload(source: str):
    """
    מטפל בהעלאת קובץ — מחזיר preview בלבד, ללא שמירה.
    השמירה מתבצעת רק כשהמשתמש לוחץ 'אישור ושמירה' → /inventory/import/confirm.
    """
    if "file" not in request.files:
        return jsonify({"error": "לא נבחר קובץ"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "שם קובץ ריק"}), 400

    save_path = UPLOAD_DIR / f.filename
    f.save(str(save_path))
    use_ai = request.form.get("use_ai", "false").lower() == "true"

    try:
        result = _parse_file(str(save_path), source, use_ai)

        # _parse_file מחזיר (None, הודעת שגיאה) אם סוג לא נתמך
        if result[0] is None:
            return jsonify({"error": result[1]}), 400

        new_items, raw_text = result

        if not new_items:
            return jsonify({
                "ok": False,
                "error": "לא זוהו פריטים בקובץ — נסה חילוץ AI",
                "raw_text": raw_text[:800] if raw_text else "",
                "preview": [],
                "filename": f.filename,
            }), 422

        return jsonify({
            "ok": True,
            "preview": new_items,
            "raw_text": raw_text[:800] if raw_text else "",  # לדיבוג
            "filename": f.filename,
        })
    except Exception as e:
        import traceback
        app.logger.error(f"Import error [{source}]: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/inventory/import/confirm", methods=["POST"])
def inventory_import_confirm():
    """שומר רשימת פריטים שאושרה על-ידי המשתמש לאחר preview"""
    data = request.get_json(silent=True) or {}
    new_items = data.get("items", [])
    source = data.get("source", "manual")
    filename = data.get("filename", "manual")

    if not new_items:
        return jsonify({"error": "אין פריטים לשמירה"}), 400

    from skills.inventory_import import merge_inventory, save_import_log
    existing = get_inventory()
    merged, log_entry = merge_inventory(existing, new_items)
    log_entry["source"]   = source
    log_entry["filename"] = filename
    log_entry["currency"] = data.get("currency", "").strip()
    log_entry["supplier"] = data.get("supplier", "").strip()

    save_json(INVENTORY_FILE, merged)
    save_import_log(log_entry)

    return jsonify({"ok": True, "log": log_entry})


@app.route("/inventory/import/ai", methods=["POST"])
def inventory_import_ai():
    """שולח טקסט חופשי ל-Claude לחילוץ מלאי"""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "טקסט ריק"}), 400

    try:
        from skills.inventory_import import ai_extract
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        items = ai_extract(text, client)
        return jsonify({"ok": True, "preview": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/inventory/import/ai-file", methods=["POST"])
def inventory_import_ai_file():
    """מחלץ טקסט מקובץ ושולח ל-Claude לחילוץ מלאי"""
    if "file" not in request.files:
        return jsonify({"error": "לא נבחר קובץ"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "שם קובץ ריק"}), 400

    save_path = UPLOAD_DIR / f.filename
    f.save(str(save_path))

    try:
        from skills.inventory_import import extract_pdf_raw_text, ai_extract
        import anthropic

        ext = Path(save_path).suffix.lower()
        raw_text = ""

        if ext == ".pdf":
            raw_text = extract_pdf_raw_text(str(save_path))
        elif ext in (".xlsx", ".xls", ".csv"):
            import pandas as pd
            try:
                df = pd.read_csv(save_path, encoding="utf-8") if ext == ".csv" else pd.read_excel(save_path)
            except Exception:
                df = pd.read_csv(save_path, encoding="cp1255") if ext == ".csv" else pd.read_excel(save_path)
            raw_text = df.to_string(index=False)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            raw_text = pytesseract.image_to_string(Image.open(str(save_path)), lang="eng+heb")
        else:
            return jsonify({"error": "סוג קובץ לא נתמך"}), 400

        if not raw_text.strip():
            return jsonify({"error": "לא ניתן לחלץ טקסט מהקובץ"}), 422

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        items = ai_extract(raw_text, client)

        if not items:
            return jsonify({
                "ok": False,
                "error": "Claude לא זיהה פריטי מלאי בקובץ",
                "raw_text": raw_text[:800],
                "preview": [],
            }), 422

        return jsonify({
            "ok": True,
            "preview": items,
            "raw_text": raw_text[:800],
            "filename": f.filename,
        })
    except Exception as e:
        import traceback
        app.logger.error(f"AI file import error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass


# --- עלות נחיתה ---

LANDED_COSTS_FILE   = DATA_DIR / "landed_costs.json"
TIRE_SPECS_FILE     = DATA_DIR / "tire_specs.json"
COST_DEFAULTS_FILE  = DATA_DIR / "cost_defaults.json"

_COST_DEFAULTS_FACTORY = {
    "freight_method":          "fixed",
    "freight_value":           3200,
    "freight_currency":        "EUR",
    "customs_pct":             0,
    "insurance_pct":           0.5,
    "customs_agent_value":     2000,
    "customs_agent_currency":  "ILS",
    "local_delivery_value":    1500,
    "local_delivery_currency": "ILS",
    "bank_fee_pct":            1.5,
    "recycling_rate":          590,
    "profit_margin":           35,
}


def get_tire_specs_data() -> dict:
    try:
        if TIRE_SPECS_FILE.exists():
            data = json.loads(TIRE_SPECS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


@app.route("/api/tire-specs")
def api_tire_specs_get():
    return jsonify(get_tire_specs_data())


@app.route("/api/tire-specs", methods=["POST"])
def api_tire_specs_save():
    incoming = request.get_json(silent=True) or {}
    specs = get_tire_specs_data()
    specs.update(incoming)
    TIRE_SPECS_FILE.write_text(
        json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jsonify({"ok": True, "saved": len(incoming)})


@app.route("/api/landed-cost/update-prices", methods=["POST"])
def api_update_sell_prices():
    data = request.get_json(silent=True) or {}
    updates = data.get("updates", [])  # [{model, size, sell_price}]
    if not updates:
        return jsonify({"error": "no updates"}), 400

    items = get_inventory()
    updated = 0
    for u in updates:
        model     = (u.get("model") or "").strip()
        size      = (u.get("size")  or "").strip()
        sell      = float(u.get("sell_price", 0))
        for item in items:
            match = (model and item.get("model") == model) or \
                    (size  and item.get("size")  == size  and not model)
            if match:
                item["sell_price"] = round(sell, 2)
                updated += 1
    if updated:
        save_json(INVENTORY_FILE, items)
    return jsonify({"ok": True, "updated": updated})


@app.route("/api/landed-cost/update-inventory", methods=["POST"])
def api_landed_cost_update_inventory():
    """מעדכן cost_price + sell_price במלאי לפי עלות נחיתה מחושבת"""
    data = request.get_json(silent=True) or {}
    updates = data.get("updates", [])  # [{model, size, landed_cost_per_unit, recommended_price}]

    # ── DEBUG ──────────────────────────────────────────────────────────────
    inv_path = os.path.abspath(INVENTORY_FILE)
    print(f"[update-inventory] inventory path : {inv_path}")
    print(f"[update-inventory] updates received: {updates}")
    # ───────────────────────────────────────────────────────────────────────

    if not updates:
        return jsonify({"error": "אין פריטים לעדכון"}), 400

    today = date.today().isoformat()
    items = get_inventory()

    # ── DEBUG ──────────────────────────────────────────────────────────────
    print(f"[update-inventory] inventory loaded : {len(items)} items")
    if items:
        print(f"[update-inventory] first item keys: {list(items[0].keys())}")
        print(f"[update-inventory] first item model: {items[0].get('model')!r}")
    # ───────────────────────────────────────────────────────────────────────

    updated = 0
    not_found = []

    for u in updates:
        model = (u.get("model") or "").strip()
        size  = (u.get("size")  or "").strip()
        cost  = float(u.get("landed_cost_per_unit", 0))
        sell  = float(u.get("recommended_price", 0))

        matched = False
        for item in items:
            inv_model = (item.get("model") or "").strip()
            # התאמה לפי מק"ט SAP בעדיפות ראשונה, אחר כך לפי מידה
            if (model and inv_model == model) or \
               (size and item.get("size") == size and not model):
                if cost > 0:
                    item["cost_price"] = round(cost, 2)
                if sell > 0:
                    item["sell_price"] = round(sell, 2)
                item["last_landed_cost_update"] = today
                updated += 1
                matched = True
                # ── DEBUG ──────────────────────────────────────────────────
                print(f"[update-inventory] matched: model={inv_model!r} size={item.get('size')!r} "
                      f"→ cost_price={item['cost_price']} sell_price={item['sell_price']}")
                # ───────────────────────────────────────────────────────────
                break

        if not matched:
            print(f"[update-inventory] NOT FOUND: model={model!r} size={size!r}")
            not_found.append(model or size)

    if updated:
        save_json(INVENTORY_FILE, items)
        print(f"[update-inventory] saved {updated} updates to {inv_path}")
        # ── DEBUG: verify first 3 items after save ─────────────────────────
        verify = [(i.get("model"), i.get("cost_price"), i.get("sell_price"))
                  for i in items[:3]]
        print(f"[update-inventory] first 3 after save: {verify}")
        # ───────────────────────────────────────────────────────────────────
    else:
        print("[update-inventory] no matches — inventory NOT saved")

    return jsonify({"ok": True, "updated": updated, "not_found": not_found})

def get_landed_costs() -> list:
    try:
        if LANDED_COSTS_FILE.exists():
            data = json.loads(LANDED_COSTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


@app.route("/landed-cost")
def landed_cost():
    return render_template("landed_cost.html")


@app.route("/api/last-import")
def api_last_import():
    """מחזיר את פרטי הייבוא האחרון מ-import_log.json"""
    log = get_import_log()
    if not log or not isinstance(log, list):
        return jsonify({"ok": False, "message": "אין ייבואים קודמים"})
    last = log[-1]
    # שדות כמות — תומך בשמות ישנים וחדשים
    items_added   = last.get("items_added",   last.get("added",   0)) or 0
    items_updated = last.get("items_updated", last.get("updated", 0)) or 0
    items_skipped = last.get("items_skipped", last.get("skipped", 0)) or 0
    total_quantity = last.get("total_quantity", items_added + items_updated)
    total_value    = last.get("total_value", 0)
    # חלץ תאריך מ-timestamp
    ts = last.get("timestamp", "")
    import_date = ts[:10] if ts else ""
    return jsonify({
        "ok":            True,
        "filename":      last.get("filename", ""),
        "source":        last.get("source", ""),
        "supplier":      last.get("supplier", ""),
        "currency":      last.get("currency", ""),
        "import_date":   import_date,
        "total_quantity": total_quantity,
        "total_value":   total_value,
        "items_added":   items_added,
        "items_updated": items_updated,
        "items_skipped": items_skipped,
    })


@app.route("/api/exchange-rate/<currency>")
def exchange_rate(currency):
    import urllib.request
    try:
        url = f"https://open.er-api.com/v6/latest/{currency.upper()}"
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read())
        rate = data.get("rates", {}).get("ILS", 0)
        return jsonify({"ok": True, "rate": round(rate, 4), "base": currency.upper()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "rate": 0})


@app.route("/api/landed-cost/analyze", methods=["POST"])
def landed_cost_analyze():
    """מנתח חשבונית יבוא עם Claude — מחזיר פרטי משלוח ורשימת פריטים"""
    if "file" not in request.files:
        return jsonify({"error": "לא נבחר קובץ"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "שם קובץ ריק"}), 400

    save_path = UPLOAD_DIR / f.filename
    f.save(str(save_path))

    try:
        ext = Path(save_path).suffix.lower()
        raw_text = ""

        if ext == ".pdf":
            from skills.inventory_import import extract_pdf_raw_text
            raw_text = extract_pdf_raw_text(str(save_path))
        elif ext in (".xlsx", ".xls", ".csv"):
            import pandas as pd
            try:
                df = pd.read_csv(save_path, encoding="utf-8") if ext == ".csv" else pd.read_excel(save_path)
            except Exception:
                df = pd.read_csv(save_path, encoding="cp1255") if ext == ".csv" else pd.read_excel(save_path)
            raw_text = df.to_string(index=False)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            import pytesseract
            from PIL import Image
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            raw_text = pytesseract.image_to_string(Image.open(str(save_path)), lang="eng+heb")
        else:
            return jsonify({"error": "סוג קובץ לא נתמך (PDF / Excel / תמונה)"}), 400

        if not raw_text.strip():
            return jsonify({"error": "לא ניתן לחלץ טקסט מהקובץ"}), 422

        import anthropic, re as _re
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = (
            "אתה מומחה לניתוח חשבוניות יבוא של צמיגים.\n"
            "קרא את הטקסט הבא וחלץ את הפרטים הבאים.\n"
            "החזר JSON בלבד, ללא טקסט נוסף:\n"
            "{\n"
            "  \"invoice_number\": \"מספר חשבונית\",\n"
            "  \"supplier\": \"שם הספק\",\n"
            "  \"date\": \"תאריך בפורמט YYYY-MM-DD\",\n"
            "  \"currency\": \"EUR או USD או GBP\",\n"
            "  \"total_value\": 0,\n"
            "  \"total_quantity\": 0,\n"
            "  \"items_count\": 0,\n"
            "  \"items\": [\n"
            "    { \"model\": \"מקט SAP\", \"size\": \"מידה\", \"quantity\": 0, \"unit_price\": 0 }\n"
            "  ]\n"
            "}\n\n"
            "חשוב:\n"
            "- currency: EUR / USD / GBP / CNY בלבד\n"
            "- date: YYYY-MM-DD בלבד\n"
            "- total_value: סכום כולל של הסחורה במטבע המקור (מספר בלבד)\n"
            "- total_quantity: סה\"כ כמות יחידות (מספר שלם)\n"
            "- items_count: מספר שורות פריטים שונות\n"
            "- items[].size: פורמט NNN/NNRNN בלבד (למשל 315/80R22.5)\n\n"
            f"טקסט החשבונית:\n{raw_text}"
        )

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_json = response.content[0].text.strip()
        raw_json = _re.sub(r"^```(?:json)?\s*", "", raw_json, flags=_re.MULTILINE)
        raw_json = _re.sub(r"\s*```\s*$",       "", raw_json, flags=_re.MULTILINE)

        try:
            result = json.loads(raw_json)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Claude החזיר JSON לא תקין: {e}", "raw": raw_json[:400]}), 422

        return jsonify({"ok": True, "data": result, "filename": f.filename})

    except Exception as e:
        import traceback
        app.logger.error(f"Landed cost analyze error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/landed-cost/save", methods=["POST"])
def landed_cost_save():
    data = request.get_json(silent=True) or {}
    calc = data.get("calc")
    if not calc:
        return jsonify({"error": "נתוני חישוב חסרים"}), 400

    calc["saved_at"] = datetime.now().isoformat(timespec="seconds")
    history = get_landed_costs()
    history.insert(0, calc)
    LANDED_COSTS_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jsonify({"ok": True, "saved_at": calc["saved_at"]})


@app.route("/api/landed-cost/history")
def api_landed_cost_history():
    """מחזיר את כל היסטוריית החישובים"""
    return jsonify(get_landed_costs())


@app.route("/api/landed-cost/load/<invoice_number>")
def load_landed_cost(invoice_number):
    """מחזיר חישוב מלא לפי מספר חשבונית"""
    history = get_landed_costs()
    for entry in history:
        num = entry.get("invoice_number") or entry.get("invoice_num", "")
        if num == invoice_number:
            return jsonify({"ok": True, "data": entry})
    return jsonify({"ok": False, "error": "חשבונית לא נמצאה"}), 404


@app.route("/api/landed-cost/history/<int:idx>", methods=["DELETE"])
def delete_landed_cost_history(idx):
    """מוחק חישוב מההיסטוריה לפי אינדקס"""
    history = get_landed_costs()
    if idx < 0 or idx >= len(history):
        return jsonify({"error": "לא נמצא"}), 404
    history.pop(idx)
    LANDED_COSTS_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jsonify({"ok": True})


# --- לקוחות ---

CUSTOMERS_FILE = DATA_DIR / "customers.json"

DEMO_CUSTOMERS = [
    {
        "id": "C001", "name": "מוסך אבי מוטורס", "phone": "03-6667788",
        "address": "רחוב הרצל 14, תל אביב", "email": "avi@avimotors.co.il",
        "contact_person": "אבי כהן", "business_id": "514123456",
        "customer_type": "מוסך", "discount_pct": 12, "payment_terms": "שוטף 30",
        "special_price_list": "מוסכים-A", "vehicles": [],
        "notes": "לקוח ותיק מ-2019. מזמין כ-20 צמיגים בחודש.",
        "status": "פעיל", "created_date": "2023-05-10", "last_purchase": "2026-03-08",
    },
    {
        "id": "C002", "name": 'חברת משלוחים מהיר בע"מ', "phone": "072-5554433",
        "address": "אזור תעשייה לוד, בניין 7", "email": "fleet@mahir.co.il",
        "contact_person": "רון אברהם", "business_id": "512987654",
        "customer_type": "ציי", "discount_pct": 18, "payment_terms": "שוטף 45",
        "special_price_list": "ציי-פרימיום",
        "vehicles": [
            {"plate": "55-222-88", "tire_size": "195/65R15"},
            {"plate": "12-345-67", "tire_size": "195/65R15"},
        ],
        "notes": "חוזה שנתי. 100 יח' בשנה.",
        "status": "פעיל", "created_date": "2024-01-15", "last_purchase": "2026-02-20",
    },
    {
        "id": "C003", "name": 'צמיגי השרון בע"מ', "phone": "09-7654321",
        "address": "נתניה, רחוב הסדנה 3", "email": "sharon@tiressharon.com",
        "contact_person": "שרה לוי", "business_id": "513456789",
        "customer_type": "קמעונאי", "discount_pct": 15, "payment_terms": "שוטף 60",
        "special_price_list": "קמעונאי-B", "vehicles": [],
        "notes": "מזמינים Michelin ו-Bridgestone בעיקר.",
        "status": "פעיל", "created_date": "2022-11-03", "last_purchase": "2026-03-01",
    },
    {
        "id": "C004", "name": "דוד לוי", "phone": "050-1234567",
        "address": "הרימון 8, ראשון לציון", "email": "david.levy@gmail.com",
        "contact_person": "", "business_id": "",
        "customer_type": "פרטי", "discount_pct": 0, "payment_terms": "מזומן",
        "special_price_list": "",
        "vehicles": [{"plate": "78-901-23", "tire_size": "205/55R16"}],
        "notes": "", "status": "פעיל", "created_date": "2025-06-20", "last_purchase": "2026-03-10",
    },
    {
        "id": "C005", "name": "מוסך גלגל זהב", "phone": "08-9001122",
        "address": "באר שבע, שדרות רגר 45", "email": "galgal@zahav.net",
        "contact_person": "יוסי גולד", "business_id": "515234567",
        "customer_type": "מוסך", "discount_pct": 10, "payment_terms": "שוטף 30",
        "special_price_list": "", "vehicles": [],
        "notes": "פעיל פחות מאז שינוי ניהול.",
        "status": "לא פעיל", "created_date": "2021-08-14", "last_purchase": "2025-09-05",
    },
    {
        "id": "C006", "name": "נועם שמיר", "phone": "058-2223344",
        "address": "הגפן 22, כפר סבא", "email": "noam.shamir@walla.com",
        "contact_person": "", "business_id": "",
        "customer_type": "פרטי", "discount_pct": 0, "payment_terms": "מזומן",
        "special_price_list": "",
        "vehicles": [{"plate": "34-567-89", "tire_size": "225/45R17"}],
        "notes": "לקוח חדש ממרץ 2026.",
        "status": "פעיל", "created_date": "2026-03-13", "last_purchase": "2026-03-13",
    },
    {
        "id": "C007", "name": 'ספינת המדע בע"מ', "phone": "04-8887766",
        "address": "חיפה, רחוב פל-ים 10", "email": "info@scienceship.co.il",
        "contact_person": "רינה גרין", "business_id": "516789012",
        "customer_type": "ציי", "discount_pct": 20, "payment_terms": "שוטף 90",
        "special_price_list": "ציי-גדול",
        "vehicles": [
            {"plate": "90-123-45", "tire_size": "215/60R16"},
            {"plate": "67-890-12", "tire_size": "215/60R16"},
        ],
        "notes": "ציי גדול. חוזה עד 12/2026.",
        "status": "מושהה", "created_date": "2023-02-28", "last_purchase": "2025-12-15",
    },
    {
        "id": "C008", "name": "יעל ברק", "phone": "053-3334455",
        "address": "צפת, שכונת הכנרת 5", "email": "yael.barak@hotmail.com",
        "contact_person": "", "business_id": "",
        "customer_type": "פרטי", "discount_pct": 0, "payment_terms": "מזומן",
        "special_price_list": "",
        "vehicles": [{"plate": "22-333-44", "tire_size": "205/60R16"}],
        "notes": "לקוחה חדשה מרץ 2026.",
        "status": "פעיל", "created_date": "2026-03-05", "last_purchase": "2026-03-05",
    },
]


def get_customers() -> list:
    return load_json(CUSTOMERS_FILE, DEMO_CUSTOMERS)


def _gen_customer_id(customers: list) -> str:
    existing = set()
    for c in customers:
        cid = str(c.get("id", ""))
        if cid.startswith("C") and cid[1:].isdigit():
            existing.add(int(cid[1:]))
    return f"C{max(existing, default=0) + 1:03d}"


def _detect_customer_columns(df) -> dict:
    col_map = {}
    cols_lower = {str(c).lower().strip(): c for c in df.columns}

    mapping = {
        "name":           ["שם", "name", "שם לקוח", "customer", "לקוח", "שם החברה"],
        "phone":          ["טלפון", "phone", "נייד", "mobile", "tel", "פלאפון"],
        "customer_type":  ["סוג", "type", "סוג לקוח", "customer_type"],
        "discount_pct":   ["הנחה", "discount", "הנחה %", "discount_pct", "%הנחה"],
        "payment_terms":  ["תנאי תשלום", "payment", "payment_terms", "תנאים"],
        "address":        ["כתובת", "address", "addr"],
        "email":          ["מייל", "email", 'דוא"ל', "mail"],
        "business_id":    ["עוסק", "ח.פ", "business_id", "vat", "מספר עוסק"],
        "status":         ["סטטוס", "status"],
        "notes":          ["הערות", "notes", "remarks"],
        "contact_person": ["איש קשר", "contact", "contact_person", "נציג"],
    }
    for field, candidates in mapping.items():
        for c in candidates:
            if c.lower() in cols_lower:
                col_map[field] = cols_lower[c.lower()]
                break
    return col_map


@app.route("/customers")
def customers_page():
    return render_template("customers.html")


@app.route("/api/customers")
def api_customers_list():
    return jsonify(get_customers())


@app.route("/api/customers", methods=["POST"])
def api_customers_add():
    data = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name:
        return jsonify({"error": "שם לקוח הוא שדה חובה"}), 400

    customers = get_customers()
    new_customer = {
        "id":                 _gen_customer_id(customers),
        "name":               name,
        "phone":              phone,
        "address":            (data.get("address") or "").strip(),
        "email":              (data.get("email") or "").strip(),
        "contact_person":     (data.get("contact_person") or "").strip(),
        "business_id":        (data.get("business_id") or "").strip(),
        "customer_type":      data.get("customer_type") or "פרטי",
        "discount_pct":       float(data.get("discount_pct") or 0),
        "payment_terms":      data.get("payment_terms") or "מזומן",
        "special_price_list": (data.get("special_price_list") or "").strip(),
        "vehicles":           data.get("vehicles") or [],
        "notes":              (data.get("notes") or "").strip(),
        "status":             data.get("status") or "פעיל",
        "created_date":       date.today().isoformat(),
        "last_purchase":      None,
    }
    customers.append(new_customer)
    save_json(CUSTOMERS_FILE, customers)
    return jsonify({"ok": True, "customer": new_customer})


@app.route("/api/customers/<cid>/update", methods=["POST"])
def api_customers_update(cid):
    data = request.get_json(silent=True) or {}
    customers = get_customers()
    for c in customers:
        if str(c.get("id")) == str(cid):
            for field in ("name", "phone", "address", "email", "contact_person",
                          "business_id", "customer_type", "payment_terms",
                          "special_price_list", "notes", "status"):
                if field in data:
                    c[field] = str(data[field]).strip() if data[field] is not None else ""
            if "discount_pct" in data:
                c["discount_pct"] = float(data["discount_pct"] or 0)
            if "vehicles" in data:
                c["vehicles"] = data["vehicles"] if isinstance(data["vehicles"], list) else []
            c["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_json(CUSTOMERS_FILE, customers)
            return jsonify({"ok": True})
    return jsonify({"error": "לקוח לא נמצא"}), 404


@app.route("/api/customers/<cid>/delete", methods=["POST"])
def api_customers_delete(cid):
    customers = get_customers()
    filtered = [c for c in customers if str(c.get("id")) != str(cid)]
    if len(filtered) == len(customers):
        return jsonify({"error": "לקוח לא נמצא"}), 404
    save_json(CUSTOMERS_FILE, filtered)
    return jsonify({"ok": True})


@app.route("/api/customers/import/excel", methods=["POST"])
def api_customers_import_excel():
    if "file" not in request.files:
        return jsonify({"error": "לא נבחר קובץ"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "שם קובץ ריק"}), 400
    save_path = UPLOAD_DIR / f.filename
    f.save(str(save_path))
    try:
        import pandas as pd
        ext = Path(save_path).suffix.lower()
        try:
            df = pd.read_csv(save_path, encoding="utf-8") if ext == ".csv" else pd.read_excel(save_path)
        except Exception:
            df = pd.read_csv(save_path, encoding="cp1255") if ext == ".csv" else pd.read_excel(save_path)
        df = df.dropna(how="all")
        col_map = _detect_customer_columns(df)
        if "name" not in col_map and "phone" not in col_map:
            return jsonify({"error": "לא ניתן לזהות עמודות שם/טלפון", "columns": list(df.columns)}), 422
        parsed = []
        for _, row in df.iterrows():
            def gcol(field):
                col = col_map.get(field)
                v = str(row.get(col, "") or "") if col else ""
                return v.strip() if v.strip() not in ("nan", "None", "") else ""
            name = gcol("name")
            if not name:
                continue
            try: discount = float(gcol("discount_pct").replace("%", "")) if gcol("discount_pct") else 0
            except (ValueError, AttributeError): discount = 0
            parsed.append({
                "name": name, "phone": gcol("phone"),
                "customer_type": gcol("customer_type") or "פרטי",
                "discount_pct": discount,
                "payment_terms": gcol("payment_terms") or "מזומן",
                "address": gcol("address"), "email": gcol("email"),
                "business_id": gcol("business_id"), "status": gcol("status") or "פעיל",
                "notes": gcol("notes"), "vehicles": [], "contact_person": "", "special_price_list": "",
            })
        if not parsed:
            return jsonify({"ok": False, "error": "לא זוהו לקוחות בקובץ"}), 422
        return jsonify({"ok": True, "customers": parsed, "filename": f.filename})
    except Exception as e:
        import traceback
        app.logger.error(f"Customer Excel import error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    finally:
        try: save_path.unlink(missing_ok=True)
        except Exception: pass


@app.route("/api/customers/import/ai", methods=["POST"])
def api_customers_import_ai():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "טקסט ריק"}), 400
    try:
        import anthropic, re as _re
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            "אתה עוזר לניהול לקוחות בעסק צמיגים. קרא את הטקסט הבא וחלץ רשימת לקוחות.\n"
            'החזר JSON בלבד: { "customers": [ { "name":"...", "phone":"...", '
            '"customer_type":"פרטי|מוסך|ציי|קמעונאי", "discount_pct":0, '
            '"payment_terms":"מזומן", "address":"", "email":"", "business_id":"", '
            '"notes":"", "status":"פעיל" } ] }\n\n'
            f"טקסט:\n{text}"
        )
        response = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = _re.sub(r"^```(?:json)?\s*", "", raw, flags=_re.MULTILINE)
        raw = _re.sub(r"\s*```\s*$", "", raw, flags=_re.MULTILINE)
        result = json.loads(raw)
        customers_data = result.get("customers", result) if isinstance(result, dict) else result
        return jsonify({"ok": True, "customers": customers_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/customers/import/confirm", methods=["POST"])
def api_customers_import_confirm():
    data = request.get_json(silent=True) or {}
    incoming = data.get("customers", [])
    selected = data.get("selected", [])
    if not incoming:
        return jsonify({"error": "אין לקוחות לייבוא"}), 400
    chosen = [incoming[i] for i in selected if 0 <= i < len(incoming)]
    if not chosen:
        return jsonify({"error": "לא נבחרו לקוחות"}), 400
    customers = get_customers()
    phone_index = {c.get("phone", "").replace("-", "").strip(): i for i, c in enumerate(customers)}
    added = updated = 0
    today = date.today().isoformat()
    for item in chosen:
        phone_clean = str(item.get("phone", "")).replace("-", "").strip()
        if phone_clean and phone_clean in phone_index:
            c = customers[phone_index[phone_clean]]
            for field in ("name", "customer_type", "discount_pct", "payment_terms",
                          "address", "email", "business_id", "notes", "status"):
                val = item.get(field)
                if val is not None and str(val).strip() not in ("", "0"):
                    c[field] = val
            updated += 1
        else:
            new_c = {
                "id": _gen_customer_id(customers),
                "name": (item.get("name") or "").strip(),
                "phone": (item.get("phone") or "").strip(),
                "address": (item.get("address") or "").strip(),
                "email": (item.get("email") or "").strip(),
                "contact_person": "", "business_id": (item.get("business_id") or "").strip(),
                "customer_type": item.get("customer_type") or "פרטי",
                "discount_pct": float(item.get("discount_pct") or 0),
                "payment_terms": item.get("payment_terms") or "מזומן",
                "special_price_list": "", "vehicles": [],
                "notes": (item.get("notes") or "").strip(),
                "status": item.get("status") or "פעיל",
                "created_date": today, "last_purchase": None,
            }
            customers.append(new_c)
            if phone_clean:
                phone_index[phone_clean] = len(customers) - 1
            added += 1
    save_json(CUSTOMERS_FILE, customers)
    return jsonify({"ok": True, "added": added, "updated": updated})


# --- ברירות מחדל עלויות ---

@app.route("/api/cost-defaults")
def api_cost_defaults_get():
    try:
        if COST_DEFAULTS_FILE.exists():
            data = json.loads(COST_DEFAULTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return jsonify(data)
    except (json.JSONDecodeError, OSError):
        pass
    return jsonify(_COST_DEFAULTS_FACTORY)


@app.route("/api/cost-defaults", methods=["POST"])
def api_cost_defaults_save():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "נתונים חסרים"}), 400
    COST_DEFAULTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jsonify({"ok": True})


# --- הצעות מחיר PDF / מייל ---

QUOTES_DIR = DATA_DIR.parent / "outputs" / "quotes"


@app.route("/api/quote/create-pdf", methods=["POST"])
def api_quote_create_pdf():
    """יוצר PDF הצעת מחיר ומחזיר שם הקובץ"""
    data     = request.get_json(silent=True) or {}
    customer = data.get("customer") or {}
    items    = data.get("items") or []
    discount = float(data.get("discount") or 0)

    if not customer.get("name"):
        return jsonify({"ok": False, "error": "שם לקוח חסר"}), 400
    if not items:
        return jsonify({"ok": False, "error": "אין פריטים"}), 400

    try:
        from skills.pdf_quote import create_quote_pdf
        pdf_path = create_quote_pdf(customer, items, discount)
        filename = Path(pdf_path).name
        return jsonify({"ok": True, "pdf_path": pdf_path, "filename": filename})
    except ImportError as e:
        return jsonify({"ok": False, "error": f"reportlab לא מותקן: {e}"}), 500
    except Exception as e:
        app.logger.error(f"PDF error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/quote/download/<filename>")
def api_quote_download(filename):
    """הורדת PDF שנוצר"""
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name  # מניעת path traversal
    file_path = QUOTES_DIR / safe
    if not file_path.exists():
        return jsonify({"error": "קובץ לא נמצא"}), 404
    return send_file(str(file_path), as_attachment=True, download_name=safe)


@app.route("/api/quote/send-email", methods=["POST"])
def api_quote_send_email():
    """שולח PDF במייל ללקוח"""
    data           = request.get_json(silent=True) or {}
    pdf_path       = (data.get("pdf_path") or "").strip()
    customer_email = (data.get("customer_email") or "").strip()
    customer_name  = (data.get("customer_name") or "").strip()
    message        = (data.get("message") or "").strip()

    if not pdf_path or not customer_email:
        return jsonify({"ok": False, "message": "pdf_path ו-customer_email נדרשים"}), 400

    try:
        from skills.email_sender import send_quote_email
        result = send_quote_email(customer_email, customer_name, pdf_path, message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/generate-pdf", methods=["POST"])
def api_generate_pdf():
    """ליצירת PDF מהצ'אט — Claude מחלץ פריטים מהטקסט הגולמי"""
    data = request.get_json(silent=True) or {}

    # תמיכה בפורמט ישן (customer+items) ובפורמט חדש (raw_text)
    raw_text      = (data.get("raw_text") or "").strip()
    customer_name = (data.get("customer_name") or
                     (data.get("customer") or {}).get("name", "")).strip()
    phone    = (data.get("phone") or (data.get("customer") or {}).get("phone", "")).strip()
    email    = (data.get("email") or (data.get("customer") or {}).get("email", "")).strip()
    discount = float(data.get("discount_pct") or data.get("discount") or 0)

    if not customer_name:
        return jsonify({"ok": False, "error": "שם לקוח חסר"}), 400

    customer = {"name": customer_name, "phone": phone,
                "email": email, "payment_terms": "מזומן"}

    # פריטים שסופקו ישירות (פורמט ישן)
    items = list(data.get("items") or [])

    # חילוץ פריטים מטקסט גולמי ע"י Claude
    if raw_text and not items:
        try:
            import anthropic as _ant, re as _re
            _client = _ant.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            _prompt = (
                "חלץ את פריטי הצעת המחיר מהטקסט הבא והחזר JSON בלבד, ללא הסברים:\n"
                '{"items": [{"description": "תיאור מלא כולל מידה ומותג", '
                '"quantity": 1, "unit_price": 0}]}\n\n'
                "הוראות:\n"
                "- description: תיאור מלא (מידה + מותג + דגם)\n"
                "- quantity: כמות (מספר שלם)\n"
                "- unit_price: מחיר יחידה (מספר בלבד, ללא ₪)\n"
                "- אל תכלול שורות סיכום (סה\"כ / הנחה / מע\"מ / תוקף)\n\n"
                f"טקסט:\n{raw_text}"
            )
            _resp = _client.messages.create(
                model="claude-sonnet-4-5", max_tokens=1000,
                messages=[{"role": "user", "content": _prompt}],
            )
            _raw = _resp.content[0].text.strip()
            _raw = _re.sub(r"^```(?:json)?\s*", "", _raw, flags=_re.MULTILINE)
            _raw = _re.sub(r"\s*```\s*$", "", _raw, flags=_re.MULTILINE)
            items = json.loads(_raw).get("items", [])
        except Exception as _e:
            app.logger.error(f"Claude extract error: {_e}")

    if not items:
        return jsonify({"ok": False, "error": "לא זוהו פריטים — הזן טקסט עם מחירים"}), 400

    # נרמול שדות
    normalized = [
        {
            "description": it.get("description", ""),
            "size":        it.get("size", ""),
            "brand":       it.get("brand", ""),
            "qty":         int(it.get("qty") or it.get("quantity") or 1),
            "unit_price":  float(it.get("unit_price", 0)),
        }
        for it in items
    ]

    try:
        from skills.pdf_quote import create_quote_pdf
        pdf_path = create_quote_pdf(customer, normalized, discount)
        filename = Path(pdf_path).name
        return jsonify({"ok": True, "pdf_path": pdf_path, "filename": filename})
    except ImportError as e:
        return jsonify({"ok": False, "error": f"reportlab לא מותקן: {e}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/download/<filename>")
def download_file(filename):
    """הורדת PDF שנוצר"""
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name
    file_path = QUOTES_DIR / safe
    if not file_path.exists():
        return jsonify({"error": "קובץ לא נמצא"}), 404
    return send_file(str(file_path), as_attachment=True, download_name=safe)


@app.route("/api/send-email", methods=["POST"])
def api_send_email():
    """שליחת מייל פשוט (מהצ'אט)"""
    data    = request.get_json(silent=True) or {}
    to      = (data.get("to_email") or "").strip()
    subject = (data.get("subject") or "הצעת מחיר").strip()
    body    = (data.get("body") or "").strip()

    if not to or "@" not in to:
        return jsonify({"ok": False, "message": "כתובת מייל לא תקינה"}), 400

    try:
        from skills.email_sender import send_simple_email
        result = send_simple_email(to, subject, body)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# --- הצעות מחיר - היסטוריה ---

QUOTES_HISTORY_FILE = DATA_DIR / "quotes_history.json"
VALID_QUOTE_STATUSES = ("נוצר", "נשלח", "אושר", "נדחה")


def get_quotes_history() -> list:
    try:
        if QUOTES_HISTORY_FILE.exists():
            data = json.loads(QUOTES_HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


@app.route("/quotes")
def quotes_page():
    quotes   = get_quotes_history()
    # וודא ש-items הוא תמיד רשימה
    for q in quotes:
        if "items" not in q or not isinstance(q.get("items"), list):
            q["items"] = []
    status_f = request.args.get("status", "")
    search   = request.args.get("search", "").strip()
    filtered = quotes
    if status_f:
        filtered = [q for q in filtered if q.get("status") == status_f]
    if search:
        s = search.lower()
        filtered = [q for q in filtered if s in q.get("customer", "").lower()
                    or s in q.get("phone", "").lower()]
    status_counts = {}
    for q in quotes:
        st = q.get("status", "נוצר")
        status_counts[st] = status_counts.get(st, 0) + 1
    return render_template("quotes.html",
                           quotes=filtered,
                           all_count=len(quotes),
                           status_counts=status_counts,
                           active_status=status_f,
                           search=search)


@app.route("/api/quotes")
def api_quotes_list():
    return jsonify(get_quotes_history())


@app.route("/api/quotes/<quote_id>/status", methods=["POST"])
def api_quote_status(quote_id):
    data       = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    if new_status not in VALID_QUOTE_STATUSES:
        return jsonify({"ok": False, "error": f"סטטוס לא תקין: {new_status}"}), 400
    history = get_quotes_history()
    for q in history:
        if q.get("id") == quote_id:
            q["status"] = new_status
            QUOTES_HISTORY_FILE.write_text(
                json.dumps(history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "הצעה לא נמצאה"}), 404


@app.route("/api/quotes/<quote_id>/send-email", methods=["POST"])
def api_quote_resend_email(quote_id):
    data    = request.get_json(silent=True) or {}
    email   = (data.get("email") or "").strip()
    history = get_quotes_history()
    quote   = next((q for q in history if q.get("id") == quote_id), None)
    if not quote:
        return jsonify({"ok": False, "message": "הצעה לא נמצאה"}), 404
    target_email = email or quote.get("email", "")
    if not target_email or "@" not in target_email:
        return jsonify({"ok": False, "message": "כתובת מייל חסרה"}), 400
    pdf_path = quote.get("pdf_path", "")
    if not pdf_path or not Path(pdf_path).exists():
        return jsonify({"ok": False, "message": "קובץ PDF לא נמצא — יש ליצור מחדש"}), 404
    try:
        from skills.email_sender import send_quote_email
        result = send_quote_email(target_email, quote.get("customer", ""), pdf_path)
        if result.get("ok"):
            quote["status"] = "נשלח"
            QUOTES_HISTORY_FILE.write_text(
                json.dumps(history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


# --- סטודיו שיווקי ---

MARKETING_DIR = Path(__file__).parent.parent / "outputs" / "marketing"


@app.route("/marketing")
def marketing_studio():
    return render_template("marketing.html")


VALID_MODELS = [
    "imagen-4.0-generate-001",
    "imagen-4.0-ultra-generate-001",
    "imagen-4.0-fast-generate-001",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image",
    "canva",
]

@app.route("/api/marketing/generate", methods=["POST"])
def api_marketing_generate():
    data   = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    visual = (data.get("visual_description") or prompt).strip()
    style  = (data.get("style")  or "מודעה מקצועית").strip()
    size   = (data.get("size")   or "1:1").strip()
    model  = (data.get("model")  or "imagen-4.0-generate-001").strip()
    texts  = data.get("texts", [])   # רשימת טקסטים עבריים לשכבה

    if model not in VALID_MODELS:
        model = "imagen-4.0-generate-001"

    if not visual:
        return jsonify({"success": False, "error": "תיאור ריק"}), 400

    # Canva — מחזיר פרומפט להעתקה
    if model == "canva":
        return jsonify({"success": True, "type": "canva", "prompt": visual})

    try:
        if texts:
            # שלב 1 — תמונה ללא טקסט
            from skills.image_generator import generate_marketing_image_no_text, add_hebrew_text
            result = generate_marketing_image_no_text(visual, size, model)
            # שלב 2 — הוסף טקסט עברי
            if result.get("success"):
                try:
                    final_path = add_hebrew_text(result["path"], texts)
                    result["path"]     = final_path
                    result["filename"] = Path(final_path).name
                except Exception as te:
                    app.logger.warning(f"Text overlay failed: {te}")
                    # מחזיר תמונה ללא טקסט
        else:
            from skills.image_generator import generate_marketing_image
            full_prompt = f"{visual}. Style: {style}" if style else visual
            result = generate_marketing_image(prompt=full_prompt, aspect_ratio=size, model=model)

        return jsonify(result)
    except EnvironmentError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Image generation error: {e}")
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str:
            return jsonify({"success": False, "error": "⚠️ חרגת ממכסת המודל. נסה Imagen 4 Fast או Canva."}), 429
        if "404" in error_str:
            return jsonify({"success": False, "error": "❌ המודל לא זמין. נסה מודל אחר."}), 404
        return jsonify({"success": False, "error": error_str}), 500


@app.route("/api/marketing/gallery")
def api_marketing_gallery():
    try:
        from skills.image_generator import get_gallery
        return jsonify(get_gallery())
    except Exception as e:
        return jsonify([])


@app.route("/outputs/marketing/<path:filename>")
def serve_marketing_image(filename):
    from flask import send_from_directory as _sfd
    import os as _os
    marketing_dir = _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "outputs", "marketing"
    )
    return _sfd(marketing_dir, _os.path.basename(filename))


@app.route("/api/marketing/delete/<filename>", methods=["POST"])
def api_marketing_delete(filename):
    safe = Path(filename).name
    file_path = MARKETING_DIR / safe
    try:
        file_path.unlink(missing_ok=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --- Rely® ---

@app.route("/rely")
def rely_page():
    from skills.rely_calculator import get_all_sizes, get_stock_status
    import json as _json
    sizes  = get_all_sizes()
    stock  = get_stock_status()
    return render_template(
        "rely.html",
        tire_sizes=sizes,
        stock=stock,
        sizes_json=_json.dumps(sizes),
    )


@app.route("/api/rely/calculate", methods=["POST"])
def api_rely_calculate():
    from skills.rely_calculator import calculate_fill
    data = request.get_json(silent=True) or {}
    result = calculate_fill(
        tire_size      = data.get("tire_size", ""),
        num_tires      = int(data.get("num_tires", 1)),
        product        = data.get("product", "T-25"),
        price_per_liter= float(data.get("price_per_liter", 0)),
    )
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/rely/stock", methods=["GET", "POST"])
def api_rely_stock():
    from skills.rely_calculator import get_stock_status, update_stock
    if request.method == "GET":
        return jsonify(get_stock_status())
    data      = request.get_json(silent=True) or {}
    product   = data.get("product", "")
    component = data.get("component", "A")
    delta     = float(data.get("delta", 0))
    result    = update_stock(product, component, delta)
    if result["success"]:
        result["stock"] = get_stock_status()
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/rely/quote-pdf", methods=["POST"])
def api_rely_quote_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    import io, datetime

    data     = request.get_json(silent=True) or {}
    customer = data.get("customer", "לקוח")
    phone    = data.get("phone", "")
    product  = data.get("product", "T-25")
    discount = float(data.get("discount", 0))
    notes    = data.get("notes", "")
    lines    = data.get("lines", [])

    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                              rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
    story = []

    # Title
    title_style = ParagraphStyle('title', fontSize=18, fontName='Helvetica-Bold',
                                 alignment=1, spaceAfter=6)
    sub_style   = ParagraphStyle('sub', fontSize=11, fontName='Helvetica',
                                 alignment=1, textColor=colors.grey, spaceAfter=14)
    body_style  = ParagraphStyle('body', fontSize=10, fontName='Helvetica', spaceAfter=4)

    story.append(Paragraph("Rely® Polyurethane Tire Fill", title_style))
    story.append(Paragraph("Quote / הצעת מחיר", sub_style))

    # Meta table
    date_str = datetime.date.today().strftime("%d/%m/%Y")
    meta = [
        ["Customer", customer, "Date", date_str],
        ["Phone",    phone,    "Product", product],
    ]
    meta_tbl = Table(meta, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    meta_tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0),(-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0),(-1,-1), 9),
        ('FONTNAME', (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0),(2,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0),(-1,-1), colors.HexColor('#F0F4FF')),
        ('GRID', (0,0),(-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 8),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # Lines table
    headers = ["Tire Size", "Qty", "L/Tire", "Total L", "Price/L", "Subtotal"]
    rows    = [headers]
    total_before = 0
    for ln in lines:
        sub = round(ln.get("subtotal", 0), 2)
        total_before += sub
        rows.append([
            ln.get("size", ""),
            str(ln.get("qty", "")),
            str(ln.get("liters", "")) + " L",
            str(round(ln.get("liters", 0) * ln.get("qty", 1), 1)) if False else
                str(round(ln.get("qty", 1) * ln.get("liters", 0), 1)) + " L",
            f"₪{ln.get('price', 0):.2f}",
            f"₪{sub:,.2f}",
        ])

    col_w = [4*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
    tbl   = Table(rows, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#1D4ED8')),
        ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
        ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTNAME',   (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('GRID',       (0,0),(-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#F8F9FF')]),
        ('TOPPADDING', (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    # Totals
    total_after = total_before * (1 - discount / 100)
    totals_data = [["Subtotal", f"₪{total_before:,.2f}"]]
    if discount:
        totals_data.append([f"Discount ({discount:.0f}%)", f"-₪{total_before - total_after:,.2f}"])
    totals_data.append(["TOTAL", f"₪{total_after:,.2f}"])

    tot_tbl = Table(totals_data, colWidths=[13*cm, 4*cm])
    tot_tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0),(-1,-1), 'Helvetica'),
        ('FONTNAME', (0,-1),(-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0),(-1,-1), 10),
        ('ALIGN', (1,0),(1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-1),(-1,-1), 1, colors.HexColor('#1D4ED8')),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('TOPPADDING', (0,0),(-1,-1), 4),
    ]))
    story.append(tot_tbl)

    if notes:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Notes: {notes}", body_style))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Curing time: 24–48 hrs | Remove valve stem before filling | Work with ventilation",
        ParagraphStyle('warn', fontSize=8, fontName='Helvetica', textColor=colors.grey)
    ))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"rely_quote_{customer}.pdf")


# --- צ'אט ---

@app.route("/chat")
def chat():
    orch = get_orchestrator()
    agents = [
        {"name": name,
         "icon": AGENT_ICONS.get(name, ("🤖", ""))[0],
         "desc": AGENT_ICONS.get(name, ("🤖", ""))[1]}
        for name in orch.agents
    ]
    return render_template("chat.html", agents=agents)


@app.route("/api/daily-report/pdf", methods=["GET"])
def api_daily_report_pdf():
    """מוריד את הדוח היומי כ-PDF"""
    try:
        agent = get_orchestrator().agents.get("סוכן דוחות")
        if not agent:
            return jsonify({"error": "סוכן דוחות לא נמצא"}), 404
        report_text = agent.daily_report()
        buffer   = _build_report_pdf(report_text, datetime.now().strftime("%d/%m/%Y"))
        filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(buffer, mimetype="application/pdf",
                         as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/daily-report", methods=["GET"])
def api_daily_report():
    """מייצר דוח יומי מלא מכל הסוכנים ושומר להיסטוריה"""
    try:
        agent = get_orchestrator().agents.get("סוכן דוחות")
        if not agent:
            return jsonify({"error": "סוכן דוחות לא נמצא"}), 404
        report = agent.daily_report()
        record = save_report_to_history(report)
        return jsonify({"ok": True, "report": report, "report_id": record["id"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/reports-history", methods=["GET"])
def api_reports_history():
    """מחזיר רשימת כל הדוחות השמורים (ללא תוכן מלא)"""
    try:
        history = json.loads(REPORTS_HISTORY_FILE.read_text(encoding="utf-8"))
        summary = [
            {"id": r["id"], "date": r["date"], "time": r["time"], "preview": r["preview"]}
            for r in history
        ]
        return jsonify({"ok": True, "reports": summary})
    except Exception:
        return jsonify({"ok": True, "reports": []})


@app.route("/api/reports-history/<int:report_id>", methods=["GET"])
def api_get_report(report_id):
    """מחזיר דוח מלא לפי ID"""
    try:
        history = json.loads(REPORTS_HISTORY_FILE.read_text(encoding="utf-8"))
        record  = next((r for r in history if r["id"] == report_id), None)
        if not record:
            return jsonify({"error": "דוח לא נמצא"}), 404
        return jsonify({"ok": True, "report": record})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/reports-history/<int:report_id>/pdf", methods=["GET"])
def api_download_old_report(report_id):
    """מוריד דוח ישן כ-PDF"""
    try:
        history = json.loads(REPORTS_HISTORY_FILE.read_text(encoding="utf-8"))
        record  = next((r for r in history if r["id"] == report_id), None)
        if not record:
            return jsonify({"error": "דוח לא נמצא"}), 404
        buffer   = _build_report_pdf(record["content"], record["date"])
        filename = f"daily_report_{record['date'].replace('/', '')}.pdf"
        return send_file(buffer, mimetype="application/pdf",
                         as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    agent_name = data.get("agent", "").strip()
    message = data.get("message", "").strip()

    if not agent_name or not message:
        return jsonify({"error": "חסרים שדות agent או message"}), 400

    agent = get_agent(agent_name)
    if agent is None:
        # fallback: חפש באורקסטרטור (כולל סוכן Rely וסוכנים עתידיים)
        agent = get_orchestrator().agents.get(agent_name)
    if agent is None:
        return jsonify({"error": f"סוכן '{agent_name}' לא נמצא"}), 404

    try:
        response = agent.chat(message, keep_history=True)
        return jsonify({"response": response, "agent": agent_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    data = request.get_json(silent=True) or {}
    agent_name = data.get("agent", "").strip()
    agent = _agent_instances.get(agent_name)
    if agent is None:
        agent = get_orchestrator().agents.get(agent_name)
    if agent:
        agent.reset_history()
    return jsonify({"ok": True})


# ── קמפיינים - Human-in-the-Loop ────────────────────────────────────

@app.route("/api/campaigns/create", methods=["POST"])
def api_create_campaign():
    """יוצר קמפיין חדש ושומר לתור אישורים"""
    try:
        data = request.get_json(silent=True) or {}
        topic         = data.get("topic", "")
        platforms     = data.get("platforms", ["פייסבוק", "אינסטגרם"])
        campaign_type = data.get("campaign_type", "פוסט")

        if not topic:
            return jsonify({"ok": False, "error": "נושא הקמפיין חסר"}), 400

        orch = get_orchestrator()
        agent = orch.agents.get("סוכן שיווק")
        if not agent:
            return jsonify({"ok": False, "error": "סוכן שיווק לא נמצא"}), 404

        campaign = agent.create_campaign(topic, platforms, campaign_type)
        return jsonify({"ok": True, "campaign": campaign})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/campaigns/queue", methods=["GET"])
def api_campaigns_queue():
    """מחזיר את כל הקמפיינים הממתינים לאישור"""
    queue = _load_campaigns_queue()
    pending = [c for c in queue if c["status"] == "ממתין_לאישור"]
    return jsonify({"ok": True, "campaigns": pending})


@app.route("/api/campaigns/<int:campaign_id>/approve", methods=["POST"])
def api_approve_campaign(campaign_id):
    """מאשר קמפיין ומפרסם אותו"""
    from datetime import datetime
    try:
        queue = _load_campaigns_queue()
        campaign = next((c for c in queue if c["id"] == campaign_id), None)
        if not campaign:
            return jsonify({"ok": False, "error": "קמפיין לא נמצא"}), 404

        campaign["status"]       = "פורסם"
        campaign["approved_at"]  = datetime.now().isoformat(timespec="seconds")
        campaign["published_at"] = datetime.now().isoformat(timespec="seconds")
        _save_campaigns_queue(queue)

        log = _load_campaigns_log()
        log.insert(0, campaign)
        _save_campaigns_log(log[:100])

        return jsonify({
            "ok": True,
            "message": f"קמפיין {campaign_id} אושר ופורסם!",
            "platforms": campaign["platforms"]
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/campaigns/<int:campaign_id>/reject", methods=["POST"])
def api_reject_campaign(campaign_id):
    """דוחה קמפיין עם סיבה"""
    try:
        data   = request.get_json(silent=True) or {}
        reason = data.get("reason", "ללא סיבה")
        queue  = _load_campaigns_queue()
        campaign = next((c for c in queue if c["id"] == campaign_id), None)
        if not campaign:
            return jsonify({"ok": False, "error": "קמפיין לא נמצא"}), 404

        campaign["status"]          = "נדחה"
        campaign["rejected_reason"] = reason
        _save_campaigns_queue(queue)

        return jsonify({"ok": True, "message": f"קמפיין {campaign_id} נדחה"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/campaigns/log", methods=["GET"])
def api_campaigns_log():
    """היסטוריית קמפיינים שפורסמו"""
    log = _load_campaigns_log()
    return jsonify({"ok": True, "campaigns": log})


# ── Auth ─────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        error = "סיסמה שגויה"
    return f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>כניסה — מערכת צמיגים AI</title>
        <style>
            *{{box-sizing:border-box;margin:0;padding:0}}
            body{{font-family:'Segoe UI',Arial,sans-serif;background:#0d1117;color:#fff;
                 display:flex;align-items:center;justify-content:center;min-height:100vh}}
            .box{{background:#161b22;border:1px solid #30363d;border-radius:12px;
                  padding:2rem;width:100%;max-width:360px;text-align:center}}
            h4{{font-size:1.1rem;margin-bottom:.25rem}}
            p{{color:#8b949e;font-size:.85rem;margin-bottom:1.5rem}}
            input{{width:100%;padding:.6rem 1rem;margin-bottom:.75rem;
                   background:#0d1117;border:1px solid #30363d;border-radius:8px;
                   color:#fff;font-size:.9rem;text-align:center;outline:none}}
            input:focus{{border-color:#58a6ff}}
            button{{width:100%;padding:.65rem;background:#238636;color:#fff;
                    border:none;border-radius:8px;font-size:.9rem;cursor:pointer}}
            button:hover{{background:#2ea043}}
            .err{{background:rgba(248,81,73,.15);border:1px solid rgba(248,81,73,.4);
                  color:#f85149;padding:.5rem;border-radius:6px;font-size:.85rem;margin-bottom:.75rem}}
        </style>
    </head>
    <body>
        <div class="box">
            <h4>🏢 מערכת צמיגים AI</h4>
            <p>כניסה לדשבורד</p>
            {"<div class='err'>"+error+"</div>" if error else ""}
            <form method="POST">
                <input type="password" name="password" placeholder="סיסמה" autofocus>
                <button type="submit">כניסה</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/health")
def health():
    try:
        agents_count = len(get_orchestrator().agents)
    except Exception:
        agents_count = 0
    return jsonify({"status": "ok", "agents": agents_count})


# ── Widget ציבורי ─────────────────────────────────────────────────────

@app.route("/widget")
def public_widget():
    """צ'אט ציבורי ללקוחות — ללא סיסמה"""
    return render_template("widget.html")


@app.route("/api/widget/chat", methods=["POST"])
def api_widget_chat():
    """API לצ'אט ציבורי — רק סוכן תמיכה"""
    data    = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "הודעה ריקה"}), 400
    try:
        agent = get_orchestrator().agents.get("סוכן תמיכה")
        reply = agent.chat(message, keep_history=False)
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── API ציבורי עם API Key ─────────────────────────────────────────────

@app.route("/api/v1/inventory", methods=["GET"])
@require_api_key
def api_v1_inventory():
    """מחזיר מלאי — לשימוש חיצוני עם API Key"""
    try:
        inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
        return jsonify({"ok": True, "inventory": inventory})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/v1/chat", methods=["POST"])
@require_api_key
def api_v1_chat():
    """Chat API — לאינטגרציות חיצוניות"""
    data       = request.get_json(silent=True) or {}
    message    = data.get("message", "")
    agent_name = data.get("agent")
    try:
        orch = get_orchestrator()
        if agent_name:
            agent = orch.agents.get(agent_name)
            if not agent:
                return jsonify({"error": "סוכן לא נמצא"}), 404
            reply = agent.chat(message, keep_history=False)
        else:
            _, reply = orch.route(message)
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    print(f"[STARTUP] DASHBOARD_PASSWORD set: {bool(os.getenv('DASHBOARD_PASSWORD'))}")
    print(f"[STARTUP] SESSION_SECRET set: {bool(os.getenv('SESSION_SECRET'))}")
    print(f"דשבורד מערכת צמיגים — http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
