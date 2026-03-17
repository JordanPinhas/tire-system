"""
pdf_quote.py — יצירת PDF הצעת מחיר מקצועית בעברית
מנגנון כפול: WeasyPrint (ראשי, HTML+CSS) → reportlab (fallback)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

OUTPUTS_DIR     = Path(__file__).parent.parent / "outputs" / "quotes"
HISTORY_FILE    = Path(__file__).parent.parent / "data" / "quotes_history.json"

COMPANY_NAME    = "מערכת צמיגים AI"
COMPANY_TAGLINE = "יבוא ושיווק צמיגים"
COMPANY_PHONE   = "04-8000001 | 03-9000001"
COMPANY_EMAIL   = "info@tires-ai.co.il"
VAT_RATE        = 0.18

# ── RTL / bidi — נדרש רק ל-reportlab fallback ──────────────────────
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    _BIDI_OK = True
except ImportError:
    _BIDI_OK = False


def fix_hebrew(text: str) -> str:
    """תיקון RTL לטקסט עברי עבור reportlab"""
    if not text:
        return ""
    text = str(text)
    if not _BIDI_OK:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


H = fix_hebrew  # קיצור


# ─────────────────────────────────────────────────────────────────────
#  ממשק ציבורי
# ─────────────────────────────────────────────────────────────────────

def create_quote_pdf(
    customer: dict,
    items: list,
    discount: float = 0,
    valid_days: int = 14,
) -> str:
    """
    יוצר PDF הצעת מחיר מקצועית.
    מנסה WeasyPrint (HTML+CSS, RTL מלא), fallback ל-reportlab.

    customer: {"name", "phone", "address", "email", "payment_terms"}
    items:    [{"description", "size", "brand", "qty", "unit_price"}]
    discount: % הנחה (0–100)
    מחזיר: נתיב לקובץ PDF שנוצר
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    quote_num = f"Q{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pdf_path  = str(OUTPUTS_DIR / f"quote_{quote_num}.pdf")

    # נסה WeasyPrint
    try:
        _create_pdf_weasyprint(customer, items, discount, valid_days, quote_num, pdf_path)
    except ImportError:
        # WeasyPrint לא מותקן — fallback ל-reportlab
        _create_pdf_reportlab(customer, items, discount, valid_days, quote_num, pdf_path)
    except Exception as e:
        print(f"[pdf_quote] WeasyPrint failed ({e}), falling back to reportlab")
        _create_pdf_reportlab(customer, items, discount, valid_days, quote_num, pdf_path)

    # שמירה להיסטוריה
    _, _, _, _, total_pay = _calc_totals(items, discount)
    _save_quote_history(quote_num, customer, items, discount, total_pay, pdf_path)

    return pdf_path


# ─────────────────────────────────────────────────────────────────────
#  עזר — חישוב מחירים
# ─────────────────────────────────────────────────────────────────────

def _calc_totals(items, discount):
    subtotal    = sum(int(it.get("qty", 1)) * float(it.get("unit_price", 0)) for it in items)
    disc_amount = subtotal * discount / 100
    after_disc  = subtotal - disc_amount
    vat_amount  = after_disc * VAT_RATE
    total_pay   = after_disc + vat_amount
    return subtotal, disc_amount, after_disc, vat_amount, total_pay


# ─────────────────────────────────────────────────────────────────────
#  מנגנון 1 — WeasyPrint (HTML+CSS)
# ─────────────────────────────────────────────────────────────────────

def _create_pdf_weasyprint(customer, items, discount, valid_days, quote_num, pdf_path):
    from weasyprint import HTML  # raises ImportError if not installed

    today     = datetime.now().strftime("%d/%m/%Y")
    valid_til = (datetime.now() + timedelta(days=valid_days)).strftime("%d/%m/%Y")
    subtotal, disc_amount, after_disc, vat_amount, total_pay = _calc_totals(items, discount)

    # ── שורות פריטים ─────────────────────────────────────────────────
    items_html = ""
    for it in items:
        qty        = int(it.get("qty", 1))
        unit_price = float(it.get("unit_price", 0))
        total_row  = qty * unit_price
        parts = [it.get("description", ""), it.get("size", ""), it.get("brand", "")]
        desc  = " ".join(p for p in parts if p).strip()
        main_desc = desc[:60]
        overflow  = desc[60:] if len(desc) > 60 else ""
        desc_html = main_desc
        if overflow:
            desc_html += f"<span class='desc-overflow'>{overflow}</span>"
        items_html += (
            f"<tr>"
            f"<td>{desc_html}</td>"
            f"<td style='text-align:center;'>{qty}</td>"
            f"<td>{unit_price:,.0f} ₪</td>"
            f"<td>{total_row:,.0f} ₪</td>"
            f"</tr>"
        )

    # ── שורת הנחה אם קיים ────────────────────────────────────────────
    discount_rows = ""
    if discount > 0:
        discount_rows = (
            f"<tr class='disc-row'><td>הנחה {discount:.0f}%</td><td>-{disc_amount:,.0f} ₪</td></tr>"
            f"<tr class='after-row'><td>לאחר הנחה</td><td>{after_disc:,.0f} ₪</td></tr>"
        )

    # ── פרטי לקוח ────────────────────────────────────────────────────
    cname  = customer.get("name", "")
    cphone = customer.get("phone", "")
    cemail = customer.get("email", "")
    caddr  = customer.get("address", "")
    cpay   = customer.get("payment_terms", "מזומן")

    cust_html = f"<strong>{cname}</strong>"
    if cphone: cust_html += f"<br>📞 {cphone}"
    if cemail: cust_html += f"<br>✉ {cemail}"
    if caddr:  cust_html += f"<br>{caddr}"

    # ── HTML מסמך ─────────────────────────────────────────────────────
    html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 1.5cm 2cm;
  }}
  body {{
    font-family: Arial, "Helvetica Neue", sans-serif;
    direction: rtl;
    color: #1f2937;
    font-size: 11pt;
    line-height: 1.5;
    margin: 0;
  }}

  /* header */
  .hdr {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #e8f0fe;
    padding: 14px 18px;
    border-radius: 6px;
    margin-bottom: 18px;
  }}
  .co-name    {{ font-size: 18pt; font-weight: bold; color: #1a2744; margin: 0 0 2px; }}
  .co-tag     {{ color: #6b7280; font-size: 10pt; margin: 0; }}
  .co-contact {{ color: #6b7280; font-size: 9pt; margin: 0; text-align: left; }}
  .dot        {{ color: #2563eb; font-size: 30pt; line-height: 1; }}

  /* title */
  .doc-title {{
    text-align: center;
    font-size: 22pt;
    font-weight: bold;
    color: #1a2744;
    margin: 0 0 14px;
  }}

  /* info grid */
  .info-grid {{
    display: flex;
    gap: 16px;
    margin-bottom: 18px;
  }}
  .info-box {{
    flex: 1;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 10px 12px;
    font-size: 10pt;
  }}
  .info-box p {{ margin: 2px 0; }}
  .lbl {{ color: #6b7280; font-weight: bold; }}

  /* section */
  .sec {{ font-size: 13pt; font-weight: bold; color: #1a2744; margin: 0 0 6px; }}

  /* items table */
  table.items {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
    font-size: 10pt;
    border: 1px solid #cbd5e1;
  }}
  table.items thead th {{
    background: #1E3A5F;
    color: white;
    padding: 8px 10px;
    text-align: right;
    border: 1px solid #16325a;
  }}
  table.items tbody tr:nth-child(even) {{ background: #f8fafc; }}
  table.items tbody tr:nth-child(odd)  {{ background: #ffffff; }}
  table.items tbody td {{
    padding: 8px 10px;
    border: 1px solid #e2e8f0;
    text-align: right;
    vertical-align: top;
  }}
  .desc-overflow {{ font-size: 8pt; color: #6b7280; display: block; }}

  /* summary table */
  table.sum {{
    margin-right: auto;
    min-width: 280px;
    border-collapse: collapse;
    font-size: 10pt;
  }}
  table.sum td {{
    padding: 6px 12px;
    border: 1px solid #cbd5e1;
    text-align: right;
  }}
  table.sum .disc-row td {{ color: #b45309; background: #fffbeb; }}
  table.sum .after-row td {{ color: #1d4ed8; }}
  table.sum .vat-row td   {{ color: #6b7280; }}
  table.sum .total-row td {{
    background: #1E3A5F;
    color: white;
    font-weight: bold;
    font-size: 11.5pt;
  }}

  /* footer */
  .footer {{
    margin-top: 28px;
    border-top: 2px solid #2563eb;
    padding-top: 8px;
    color: #6b7280;
    font-size: 9pt;
    text-align: center;
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="hdr">
  <p class="co-contact">{COMPANY_PHONE}<br>{COMPANY_EMAIL}</p>
  <div style="text-align:right;">
    <p class="co-name">{COMPANY_NAME}</p>
    <p class="co-tag">{COMPANY_TAGLINE}</p>
  </div>
  <span class="dot">●</span>
</div>

<!-- Title -->
<h1 class="doc-title">הצעת מחיר</h1>

<!-- Info grid -->
<div class="info-grid">
  <div class="info-box">
    <p><span class="lbl">לכבוד:</span> {cust_html}</p>
    <p><span class="lbl">תנאי תשלום:</span> {cpay}</p>
  </div>
  <div class="info-box">
    <p><span class="lbl">מס׳ הצעה:</span> {quote_num}</p>
    <p><span class="lbl">תאריך:</span> {today}</p>
    <p><span class="lbl">תוקף עד:</span> {valid_til}</p>
  </div>
</div>

<!-- Items table -->
<p class="sec">פרטי ההצעה</p>
<table class="items">
  <thead>
    <tr>
      <th>תיאור / מידה</th>
      <th style="text-align:center;">כמות</th>
      <th>מחיר יח׳ ₪</th>
      <th>סה"כ ₪</th>
    </tr>
  </thead>
  <tbody>
    {items_html}
  </tbody>
</table>

<!-- Summary -->
<table class="sum">
  <tbody>
    <tr><td>סכום לפני הנחה</td><td>{subtotal:,.0f} ₪</td></tr>
    {discount_rows}
    <tr class="vat-row"><td>מע"מ {int(VAT_RATE * 100)}%</td><td>+ {vat_amount:,.0f} ₪</td></tr>
    <tr class="total-row"><td><strong>סה"כ לתשלום</strong></td><td><strong>{total_pay:,.0f} ₪</strong></td></tr>
  </tbody>
</table>

<!-- Footer -->
<div class="footer">
  <p>הצעה זו בתוקף עד {valid_til}. תודה על הפנייה! נשמח לעמוד לשירותכם.</p>
  <p>חתימה: _______________________&nbsp;&nbsp;&nbsp;&nbsp;{COMPANY_NAME}</p>
</div>

</body>
</html>"""

    HTML(string=html_content).write_pdf(pdf_path)


# ─────────────────────────────────────────────────────────────────────
#  מנגנון 2 — reportlab (fallback)
# ─────────────────────────────────────────────────────────────────────

def _create_pdf_reportlab(customer, items, discount, valid_days, quote_num, pdf_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table,
            TableStyle, HRFlowable,
        )
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    except ImportError:
        raise ImportError("גם reportlab לא מותקן — נא להתקין: pip install reportlab")

    _register_hebrew_font()
    FONT = _get_font_name()

    today     = datetime.now().strftime("%d/%m/%Y")
    valid_til = (datetime.now() + timedelta(days=valid_days)).strftime("%d/%m/%Y")
    subtotal, disc_amount, after_disc, vat_amount, total_pay = _calc_totals(items, discount)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title=f"הצעת מחיר — {customer.get('name', '')}",
    )

    DARK   = HexColor("#1a2744")
    NAVY   = HexColor("#1E3A5F")
    BLUE   = HexColor("#2563eb")
    LIGHT  = HexColor("#e8f0fe")
    GRAY   = HexColor("#6b7280")
    LGRAY  = HexColor("#f8fafc")
    YELLOW = HexColor("#fffbeb")

    def style(size=10, bold=False, color=black, align=TA_RIGHT):
        return ParagraphStyle(
            "s", fontName=FONT, fontSize=size, textColor=color,
            alignment=align, leading=size * 1.55,
        )

    story = []

    # כותרת עליונה
    hdr = Table([[
        Paragraph(f"{COMPANY_PHONE}<br/>{COMPANY_EMAIL}", style(9, color=GRAY)),
        Paragraph(f"<b>{H(COMPANY_NAME)}</b><br/>{H(COMPANY_TAGLINE)}", style(15, color=DARK)),
        Paragraph("●", style(36, color=BLUE, align=TA_LEFT)),
    ]], colWidths=[5.5 * cm, 8 * cm, 2 * cm])
    hdr.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story += [hdr, Spacer(1, 0.5 * cm)]

    story.append(Paragraph(H("הצעת מחיר"), style(22, bold=True, color=DARK, align=TA_CENTER)))
    story.append(Spacer(1, 0.35 * cm))

    cname  = H(customer.get("name", "—"))
    cphone = customer.get("phone", "")
    caddr  = H(customer.get("address", ""))
    cemail = customer.get("email", "")
    cpay   = H(customer.get("payment_terms", "מזומן"))

    cust_lines = f"<b>{H('לקוח:')}</b> {cname}<br/>"
    if cphone: cust_lines += f"<b>{H('טלפון:')}</b> {cphone}<br/>"
    if caddr:  cust_lines += f"<b>{H('כתובת:')}</b> {caddr}<br/>"
    if cemail: cust_lines += f"<b>{H('מייל:')}</b> {cemail}"

    info = Table([[
        Paragraph(
            f"<b>{H('מס׳ הצעה:')}</b> {quote_num}<br/>"
            f"<b>{H('תאריך:')}</b> {today}<br/>"
            f"<b>{H('תוקף עד:')}</b> {valid_til}<br/>"
            f"<b>{H('תנאי תשלום:')}</b> {cpay}",
            style(10),
        ),
        Paragraph(cust_lines, style(10)),
    ]], colWidths=[7.75 * cm, 7.75 * cm])
    info.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
        ("BACKGROUND",    (0, 0), (-1, -1), LGRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story += [info, Spacer(1, 0.5 * cm)]

    story.append(Paragraph(H("פרטי ההצעה"), style(12, bold=True, color=DARK)))
    story.append(Spacer(1, 0.2 * cm))

    hdrs = [H('סה"כ ₪'), H("מחיר יח' ₪"), H("כמות"), H("תיאור / מידה")]
    rows = [[Paragraph(h, style(9, bold=True)) for h in hdrs]]

    for it in items:
        qty        = int(it.get("qty", 1))
        unit_price = float(it.get("unit_price", 0))
        total_row  = qty * unit_price
        parts = [it.get("description", ""), it.get("size", ""), it.get("brand", "")]
        full_desc = " ".join(p for p in parts if p).strip()
        main_desc = H(full_desc[:60])
        overflow  = H(full_desc[60:]) if len(full_desc) > 60 else ""
        desc_txt  = main_desc + (f"<br/><font size='7' color='#6b7280'>{overflow}</font>" if overflow else "")
        rows.append([
            Paragraph(f"{total_row:,.0f}", style(9, align=TA_LEFT)),
            Paragraph(f"{unit_price:,.0f}", style(9, align=TA_LEFT)),
            Paragraph(str(qty),             style(9, align=TA_CENTER)),
            Paragraph(desc_txt,             style(9)),
        ])

    items_tbl = Table(rows, colWidths=[3 * cm, 3 * cm, 2 * cm, 7.5 * cm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LGRAY]),
        ("GRID",           (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("TOPPADDING",     (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    story += [items_tbl, Spacer(1, 0.5 * cm)]

    sum_rows_raw = [(H("סכום לפני הנחה"), f"{subtotal:,.0f} ₪", "normal")]
    if discount > 0:
        sum_rows_raw.append((H(f"הנחה {discount:.0f}%"), f"-{disc_amount:,.0f} ₪", "disc"))
        sum_rows_raw.append((H("לאחר הנחה"), f"{after_disc:,.0f} ₪", "after"))
    sum_rows_raw.append((H(f'מע"מ {int(VAT_RATE * 100)}%'), f"+ {vat_amount:,.0f} ₪", "vat"))
    sum_rows_raw.append((H('סה"כ לתשלום'), f"{total_pay:,.0f} ₪", "total"))

    sum_data = [
        [Paragraph(k, style(10, bold=(t == "total"), color=(white if t == "total" else black))),
         Paragraph(v, style(10, bold=(t == "total"), align=TA_LEFT, color=(white if t == "total" else black)))]
        for k, v, t in sum_rows_raw
    ]
    sum_tbl = Table(sum_data, colWidths=[5.2 * cm, 3.2 * cm], hAlign="RIGHT")
    disc_indices  = [i for i, (_, _, t) in enumerate(sum_rows_raw) if t == "disc"]
    total_indices = [i for i, (_, _, t) in enumerate(sum_rows_raw) if t == "total"]
    style_cmds = [
        ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]
    for i in disc_indices:
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), YELLOW))
        style_cmds.append(("TEXTCOLOR",  (0, i), (-1, i), HexColor("#b45309")))
    for i in total_indices:
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), NAVY))
        style_cmds.append(("TEXTCOLOR",  (0, i), (-1, i), white))
        style_cmds.append(("FONTSIZE",   (0, i), (-1, i), 11))
    sum_tbl.setStyle(TableStyle(style_cmds))
    story += [sum_tbl, Spacer(1, 1 * cm)]

    story.append(HRFlowable(color=BLUE, thickness=1.5))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        H(f"הצעה זו בתוקף עד {valid_til}. תודה על הפנייה! נשמח לעמוד לשירותכם."),
        style(9, color=GRAY, align=TA_CENTER),
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        H(f"חתימה: _______________________                {COMPANY_NAME}"),
        style(9),
    ))

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────
#  היסטוריה
# ─────────────────────────────────────────────────────────────────────

def _save_quote_history(quote_id, customer, items, discount, total, pdf_path):
    try:
        record = {
            "id":       quote_id,
            "date":     datetime.now().strftime("%Y-%m-%d"),
            "time":     datetime.now().strftime("%H:%M"),
            "customer": customer.get("name", ""),
            "phone":    customer.get("phone", ""),
            "email":    customer.get("email", ""),
            "items":    items,
            "discount": discount,
            "total":    round(total),
            "pdf_path": pdf_path,
            "status":   "נוצר",
        }
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                if not isinstance(history, list):
                    history = []
            except Exception:
                history = []
        history.insert(0, record)
        HISTORY_FILE.write_text(
            json.dumps(history[:200], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_quote_history() -> list:
    try:
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def update_quote_status(quote_id: str, new_status: str) -> bool:
    try:
        history = get_quote_history()
        for q in history:
            if q.get("id") == quote_id:
                q["status"] = new_status
                HISTORY_FILE.write_text(
                    json.dumps(history, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────
#  גופן עברי ל-reportlab
# ─────────────────────────────────────────────────────────────────────

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"


def _register_hebrew_font():
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\Tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Arial.ttf",
    ]
    for fp in candidates:
        if Path(fp).exists():
            try:
                pdfmetrics.registerFont(TTFont("Hebrew", fp))
                _FONT_NAME = "Hebrew"
                _FONT_REGISTERED = True
                return
            except Exception:
                continue
    _FONT_REGISTERED = True


def _get_font_name() -> str:
    _register_hebrew_font()
    return _FONT_NAME


# ─────────────────────────────────────────────────────────────────────
#  עזר — פורמט קצר לצ'אט
# ─────────────────────────────────────────────────────────────────────

def format_quote_for_chat(customer_name: str, items: list, discount: float, valid_days: int = 14) -> str:
    subtotal, disc_amount, _, _, total_pay = _calc_totals(items, discount)

    lines = [f"📋 הצעת מחיר — {customer_name}", ""]
    for it in items:
        desc  = it.get("description") or f"{it.get('size', '')} {it.get('brand', '')}".strip()
        qty   = int(it.get("qty", 1))
        price = float(it.get("unit_price", 0))
        lines.append(f"• {desc}  ×{qty} יח' — {qty * price:,.0f} ₪")
    if discount > 0:
        lines.append(f"\nהנחה: {discount}%  (-{disc_amount:,.0f} ₪)")
    lines.append(f'סה"כ + מע"מ: {total_pay:,.0f} ₪')
    valid_til = (datetime.now() + timedelta(days=valid_days)).strftime("%d/%m/%Y")
    lines.append(f"תוקף: {valid_til}")
    return "\n".join(lines)
