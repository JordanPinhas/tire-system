"""
skills/inventory_import.py
ייבוא מלאי ממקורות שונים: Excel, PDF, תמונה, AI
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path


# ---- פונקציות עזר ----

def _normalize_key(item: dict) -> str:
    """מפתח ייחודי לפריט: מותג+דגם+מידה (lower, stripped)"""
    brand = str(item.get("brand", "")).strip().lower()
    model = str(item.get("model", "")).strip().lower()
    size  = str(item.get("size", "")).strip().lower().replace(" ", "")
    return f"{brand}|{model}|{size}"


def _parse_number(val) -> float:
    """המרת ערך מספרי גמיש (כולל מחרוזות עם פסיקים/סימנים)"""
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("₪", "").replace(" ", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _clean_item(raw: dict) -> dict | None:
    """
    מנרמל פריט גולמי למבנה אחיד.
    מחזיר None אם מידה חסרה.
    """
    # מיפוי שמות עמודות אנגלית/עברית אפשריים
    BRAND_KEYS      = ["brand", "מותג", "יצרן", "Brand"]
    MODEL_KEYS      = ["model", "דגם", "Model", "type", "סוג"]
    TIRE_MODEL_KEYS = ["tire_model", "דגם_מסחרי", "product_name", "commercial_model", "pattern"]
    SIZE_KEYS       = ["size", "מידה", "גודל", "Size", "tire_size", "dimension"]
    QTY_KEYS        = ["quantity", "qty", "כמות", "Qty", "Quantity", "stock", "מלאי"]
    COST_KEYS       = ["cost_price", "cost", "עלות", "Cost", "price", "מחיר_עלות", "purchase_price"]
    SELL_KEYS       = ["sell_price", "selling_price", "מחיר_מכירה", "מחיר", "Sell", "retail"]
    MIN_KEYS        = ["min_qty", "minimum", "מינימום", "min", "Min"]

    def pick(d, keys):
        for k in keys:
            if k in d and d[k] not in (None, "", "nan"):
                return d[k]
        return None

    size = pick(raw, SIZE_KEYS)
    if not size or str(size).strip() in ("", "nan", "None"):
        return None  # מידה היא שדה חובה

    return {
        "brand":      str(pick(raw, BRAND_KEYS) or "לא ידוע").strip(),
        "model":      str(pick(raw, MODEL_KEYS) or "").strip(),
        "tire_model": str(pick(raw, TIRE_MODEL_KEYS) or "").strip(),
        "size":       str(size).strip(),
        "quantity":   int(_parse_number(pick(raw, QTY_KEYS)) or 0),
        "cost_price": _parse_number(pick(raw, COST_KEYS)) or 0.0,
        "sell_price": _parse_number(pick(raw, SELL_KEYS)) or 0.0,
        "min_qty":    int(_parse_number(pick(raw, MIN_KEYS)) or 10),
    }


# ---- ייבוא מ-Excel / CSV ----

def import_from_excel(file_path: str) -> list[dict]:
    """
    קורא קובץ Excel (.xlsx/.xls) או CSV והופך לרשימת פריטים.
    מחזיר רשימה ריקה אם pandas לא מותקן.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas לא מותקן. הרץ: pip install pandas openpyxl")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"קובץ לא נמצא: {file_path}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            # נסה קידוד utf-8, לאחר מכן cp1255 (עברית)
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="cp1255")
        else:
            df = pd.read_excel(path)
    except Exception as e:
        raise ValueError(f"שגיאה בקריאת הקובץ: {e}")

    # הסר שורות ריקות לחלוטין
    df = df.dropna(how="all")

    items = []
    for _, row in df.iterrows():
        raw = {k: (None if str(v) in ("nan", "NaN", "None", "") else v)
               for k, v in row.to_dict().items()}
        item = _clean_item(raw)
        if item:
            items.append(item)

    return items


# ---- ייבוא Linglong / Hubtrac PDF ----

# זיהוי שם ספק (לשימוש עתידי)
_SUPPLIER_RE = re.compile(r"\b(LINGLONG|HUBTRAC|TRIANGLE|DOUBLESTAR)\b", re.IGNORECASE)


def extract_pdf_raw_text(file_path: str) -> str:
    """מחלץ טקסט גולמי מ-PDF — משמש לדיבוג ול-AI fallback."""
    try:
        import fitz
    except ImportError:
        return ""
    path = Path(file_path)
    if not path.exists():
        return ""
    doc = fitz.open(str(path))
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def import_from_linglong_pdf(file_path: str) -> list[dict]:
    """
    ייבוא חשבוניות Linglong / Hubtrac באמצעות Claude API.
    מחלץ טקסט גולמי מה-PDF ושולח ל-claude-sonnet-4-5 לפרסור.
    זורק ValueError אם API key חסר או Claude מחזיר תוצאה ריקה.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"קובץ לא נמצא: {file_path}")

    raw_text = extract_pdf_raw_text(str(path))
    if not raw_text.strip():
        raise ValueError("לא ניתן לחלץ טקסט מה-PDF")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY לא מוגדר ב-.env")

    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic לא מותקן. הרץ: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "אתה מומחה לקריאת חשבוניות צמיגים.\n"
        "קרא את הטקסט הבא מחשבונית וחלץ את כל הפריטים.\n"
        "החזר JSON בלבד, ללא טקסט נוסף, בפורמט הזה:\n"
        "[\n"
        "  {\n"
        "    \"brand\": \"שם המותג מהכותרת (למשל: LINGLONG)\",\n"
        "    \"model\": \"SAP CODE בלבד — ספרות בלבד, המספר הראשון בשורה (למשל: 211017626)\",\n"
        "    \"tire_model\": \"שם הדגם המסחרי בלבד — החלק האחרון של התיאור (למשל: REGIONAL D22, MIXED D21, HIGHWAY S11)\",\n"
        "    \"size\": \"מידת הצמיג בלבד בפורמט NNN/NNRNN (למשל: 315/80R22.5) — ללא הסיומות כמו -20, -18, TL, TT\",\n"
        "    \"description\": \"התיאור המלא כולל הכל (למשל: 315/80R22.5-20 TL 156/150L REGIONAL D22)\",\n"
        "    \"quantity\": 20,\n"
        "    \"cost_price\": 201.12,\n"
        "    \"min_qty\": 5\n"
        "  }\n"
        "]\n\n"
        "חשוב:\n"
        "- model = ספרות SAP בלבד (לדוגמה: 211017626)\n"
        "- tire_model = שם הדגם המסחרי בלבד (לדוגמה: REGIONAL D22)\n"
        "- size = מידה בלבד ללא שום תוסף (לדוגמה: 315/80R22.5)\n"
        "- description = התיאור המלא כפי שמופיע בחשבונית\n\n"
        f"טקסט החשבונית:\n{raw_text}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_json = response.content[0].text.strip()
    # נקה markdown code blocks אם קיימים
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
    raw_json = re.sub(r"\s*```\s*$",       "", raw_json, flags=re.MULTILINE)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude החזיר JSON לא תקין: {e}\nתגובה: {raw_json[:200]}")

    if not isinstance(data, list) or not data:
        raise ValueError("Claude לא מצא פריטים בחשבונית")

    items = []
    for row in data:
        size_str = str(row.get("size", "")).strip()
        if not size_str:
            continue
        items.append({
            "brand":       str(row.get("brand", "Linglong")).strip(),
            "model":       str(row.get("model", "")).strip(),
            "tire_model":  str(row.get("tire_model", "")).strip(),
            "size":        size_str,
            "description": str(row.get("description", "")).strip(),
            "quantity":    int(_parse_number(row.get("quantity", 0))),
            "cost_price":  _parse_number(row.get("cost_price", 0)),
            "sell_price":  0.0,
            "min_qty":     int(_parse_number(row.get("min_qty", 5))),
        })

    if not items:
        raise ValueError("לא זוהו פריטים תקינים בתגובת Claude")

    return items


def import_from_pdf(file_path: str) -> list[dict]:
    """
    מחלץ טקסט מ-PDF באמצעות PyMuPDF ומנסה לזהות שורות צמיגים.
    אם לא מוצא שורות מובנות — מחזיר את הטקסט הגולמי ב-raw_text.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF לא מותקן. הרץ: pip install pymupdf")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"קובץ לא נמצא: {file_path}")

    doc = fitz.open(str(path))
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()

    return _parse_text_to_items(full_text)


# ---- ייבוא מתמונה (OCR) ----

def import_from_image(file_path: str) -> list[dict]:
    """
    מריץ OCR על תמונה/סריקה של חשבונית באמצעות pytesseract.
    """
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    except ImportError:
        raise ImportError("pytesseract/Pillow לא מותקנים. הרץ: pip install pytesseract pillow")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"קובץ לא נמצא: {file_path}")

    img = Image.open(str(path))
    # שפות: עברית + אנגלית
    try:
        text = pytesseract.image_to_string(img, lang="heb+eng")
    except Exception:
        text = pytesseract.image_to_string(img)

    return _parse_text_to_items(text)


# ---- פרסור טקסט חופשי ----

# ביטוי רגולרי לזיהוי מידת צמיג (למשל 205/55R16)
_SIZE_RE = re.compile(r"\b\d{3}/\d{2,3}[Rr]\d{2}\b")

def _parse_text_to_items(text: str) -> list[dict]:
    """
    מנסה לחלץ פריטי מלאי מטקסט חופשי.
    מחפש שורות שמכילות מידת צמיג (NNN/NNRnn).
    """
    items = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = _SIZE_RE.search(line)
        if not m:
            continue

        size = m.group(0)
        # חלץ מספרים מהשורה
        numbers = re.findall(r"\b\d+(?:[.,]\d+)?\b", line.replace(size, ""))
        floats = [_parse_number(n) for n in numbers]

        # ניחוש מותג: המילה הראשונה בשורה (לפני המידה)
        before_size = line[:m.start()].strip()
        tokens = before_size.split()
        brand = tokens[0] if tokens else "לא ידוע"
        model = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        # מספרים: ראשון = כמות, שני = עלות, שלישי = מחיר מכירה
        qty       = int(floats[0]) if len(floats) > 0 else 0
        cost      = floats[1]      if len(floats) > 1 else 0.0
        sell      = floats[2]      if len(floats) > 2 else 0.0

        items.append({
            "brand":      brand,
            "model":      model,
            "size":       size,
            "quantity":   qty,
            "cost_price": cost,
            "sell_price": sell,
            "min_qty":    10,
        })

    return items


# ---- חילוץ AI (Claude) ----

def ai_extract(text: str, client) -> list[dict]:
    """
    שולח טקסט גולמי ל-Claude וביקשה ממנו להחזיר JSON של פריטי מלאי.
    client: anthropic.Anthropic instance
    """
    system = (
        "אתה מומחה לחילוץ נתוני מלאי צמיגים. "
        "קבל טקסט גולמי מחשבונית או רשימת מלאי ומחזיר JSON בלבד — "
        "מערך של אובייקטים עם השדות הבאים:\n"
        "- brand: שם המותג בלבד (למשל: LINGLONG, Michelin)\n"
        "- model: SAP CODE בלבד — ספרות בלבד (למשל: 211017626). לא לכלול מידה או תיאור.\n"
        "- tire_model: שם הדגם המסחרי בלבד (למשל: REGIONAL D22, MIXED D21, Primacy 4). לא לכלול מידה.\n"
        "- size: מידת הצמיג בלבד בפורמט NNN/NNRNN (למשל: 315/80R22.5). ללא -20, -18, TL, TT, דירוגי עומס/מהירות.\n"
        "- description: תיאור מלא כפי שמופיע במקור\n"
        "- quantity: כמות (מספר שלם)\n"
        "- cost_price: מחיר עלות (מספר עשרוני)\n"
        "- sell_price: מחיר מכירה (0 אם לא קיים)\n"
        "- min_qty: כמות מינימום (ברירת מחדל: 5)\n"
        "החזר רק JSON תקין ללא טקסט נוסף."
    )
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"חלץ מלאי מהטקסט הבא:\n\n{text}"}],
    )
    raw_json = response.content[0].text.strip()
    # נקה markdown code blocks אם קיימים
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
    raw_json = re.sub(r"\s*```$", "", raw_json, flags=re.MULTILINE)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        # לפעמים Claude מחזיר {"items": [...]}
        for key in ("items", "inventory", "data", "tires"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            return []

    items = []
    for raw in data:
        item = _clean_item(raw)
        if item:
            items.append(item)
    return items


# ---- מיזוג חכם ----

def merge_inventory(existing: list[dict], new_items: list[dict]) -> tuple[list[dict], dict]:
    """
    מוזג פריטים חדשים לתוך המלאי הקיים.
    מפתח מיזוג: brand + model + size (מנורמל).
    אם הפריט קיים — מוסיף כמות.
    אם חדש — מוסיף ברשימה עם id חדש.

    מחזיר: (merged_list, log_entry)
    """
    # בנה אינדקס של פריטים קיימים
    index: dict[str, int] = {}  # key -> index in merged
    merged = [dict(item) for item in existing]
    for i, item in enumerate(merged):
        k = _normalize_key(item)
        index[k] = i

    next_id = max((item.get("id", 0) for item in merged), default=0) + 1

    added = 0
    updated = 0
    skipped = 0

    for new in new_items:
        if not new.get("size"):
            skipped += 1
            continue
        k = _normalize_key(new)
        if k in index:
            # עדכן כמות
            i = index[k]
            merged[i]["quantity"] = merged[i].get("quantity", 0) + new.get("quantity", 0)
            # עדכן מחירים רק אם חסרים
            if not merged[i].get("cost_price") and new.get("cost_price"):
                merged[i]["cost_price"] = new["cost_price"]
            if not merged[i].get("sell_price") and new.get("sell_price"):
                merged[i]["sell_price"] = new["sell_price"]
            updated += 1
        else:
            # הוסף פריט חדש
            new_item = dict(new)
            new_item["id"] = next_id
            next_id += 1
            merged.append(new_item)
            index[k] = len(merged) - 1
            added += 1

    total_quantity = sum(int(i.get("quantity", 0)) for i in new_items)
    total_value    = sum(
        float(i.get("cost_price", 0)) * int(i.get("quantity", 0))
        for i in new_items
    )

    log_entry = {
        "timestamp":      datetime.now().isoformat(timespec="seconds"),
        "items_added":    added,
        "items_updated":  updated,
        "items_skipped":  skipped,
        "total_new":      len(new_items),
        "total_quantity": total_quantity,
        "total_value":    round(total_value, 2),
        # שדות אופציונליים — ימולאו מה-caller אם זמינים
        "currency":       "",
        "supplier":       "",
    }

    return merged, log_entry


# ---- שמירת לוג ייבוא ----

LOG_PATH = Path(__file__).parent.parent / "data" / "import_log.json"


def save_import_log(log_entry: dict):
    """מוסיף ערך לוג לקובץ import_log.json"""
    logs = []
    if LOG_PATH.exists():
        try:
            logs = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logs = []
    logs.append(log_entry)
    LOG_PATH.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
