"""
web_search.py — חיפוש מחירי מתחרים לצמיגים
"""

import re
from typing import Optional

try:
    import requests
    _requests_ok = True
except ImportError:
    _requests_ok = False

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

_PRICE_RE = re.compile(r"₪\s*([\d,]+)|([\d,]+)\s*₪|([\d,]+)\s*שקל")


def search_competitor_prices(tire_size: str, brand: str = "") -> list:
    """
    מחפשת מחירי מתחרים לצמיג ספציפי.
    מחזירה עד 5 תוצאות: [{"source", "price", "title", "url"}]
    """
    if not tire_size:
        return [{"source": "—", "price": None, "title": "לא הוזנה מידת צמיג", "url": ""}]

    if not _requests_ok:
        return _fallback_prices(tire_size, brand)

    query = f"מחיר צמיג {tire_size} {brand} ₪ ישראל".strip()

    try:
        results = _google_search(query, tire_size)
        if not results:
            results = _fallback_prices(tire_size, brand)
        return results[:5]
    except Exception as e:
        return [{"source": "שגיאה", "price": None, "title": str(e), "url": ""}]


def _google_search(query: str, tire_size: str) -> list:
    """שולח בקשת חיפוש ל-Google ומחלץ תוצאות"""
    try:
        url  = f"https://www.google.com/search?q={requests.utils.quote(query)}&hl=iw&gl=il&num=10"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        return _parse_html(resp.text, tire_size)
    except Exception:
        return []


def _parse_html(html: str, tire_size: str) -> list:
    """מנתח HTML של Google ומחלץ מחירים ותוצאות"""
    results = []

    # ניקוי HTML בסיסי
    clean = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL)
    clean = re.sub(r"<script[^>]*>.*?</script>", " ", clean, flags=re.DOTALL)

    # פיצול לבלוקים של תוצאות
    blocks = re.split(r'<div[^>]+class="[^"]*(?:tF2Cxc|g\s)[^"]*"', clean)

    for block in blocks[1:10]:
        # כותרת
        title_m = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
        title   = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

        # URL
        url_m = re.search(r'href="(https?://[^"&]+)"', block)
        url   = url_m.group(1) if url_m else ""

        # מחיר
        plain = re.sub(r"<[^>]+>", " ", block)
        price = _extract_price(plain)

        # מקור
        domain_m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        source   = domain_m.group(1) if domain_m else "google.com"

        if title and (price or tire_size.replace("/", "").replace("R", "") in plain.replace("/", "").replace("R", "")):
            results.append({
                "source": source,
                "price":  price,
                "title":  title[:80],
                "url":    url[:200],
            })

    # fallback: מחירים גלובליים בעמוד
    if not results:
        plain_all = re.sub(r"<[^>]+>", " ", html)
        prices    = _find_all_prices(plain_all)
        if prices:
            avg = int(sum(prices) / len(prices))
            results = [{
                "source": "google.com",
                "price":  avg,
                "title":  f"ממוצע מחיר {tire_size} בשוק (מתוך {len(prices)} תוצאות)",
                "url":    f"https://www.google.com/search?q={tire_size}",
            }]

    return results


def _extract_price(text: str) -> Optional[int]:
    """מחלץ מחיר שקלי ראשון מטקסט"""
    for m in _PRICE_RE.finditer(text):
        raw = (m.group(1) or m.group(2) or m.group(3) or "").replace(",", "")
        try:
            p = int(raw)
            if 100 <= p <= 15000:
                return p
        except ValueError:
            continue
    return None


def _find_all_prices(text: str) -> list:
    """מוצא את כל המחירים השקליים בטקסט"""
    prices = []
    for m in _PRICE_RE.finditer(text):
        raw = (m.group(1) or m.group(2) or m.group(3) or "").replace(",", "")
        try:
            p = int(raw)
            if 150 <= p <= 10000:
                prices.append(p)
        except ValueError:
            continue
    return prices


def _fallback_prices(tire_size: str, brand: str) -> list:
    """
    מחירי עזר כשאין גישה לאינטרנט.
    מבוסס על טווחי מחירים ממוצעים בשוק הישראלי.
    """
    m = re.search(r"(\d{3})/(\d{2,3})[Rr](\d{2})", tire_size)
    if not m:
        return [{"source": "—", "price": None, "title": "לא ניתן להעריך", "url": ""}]

    width, aspect, rim = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # הערכה לפי גודל גלגל
    if rim >= 22:
        base = 1800
    elif rim >= 20:
        base = 1200
    elif rim >= 18:
        base = 550
    elif rim >= 17:
        base = 420
    else:
        base = 320

    # תוספת לפי מותג
    brand_upper = (brand or "").upper()
    if any(b in brand_upper for b in ["MICHELIN", "BRIDGESTONE", "CONTINENTAL", "PIRELLI"]):
        mult = 1.5
    elif any(b in brand_upper for b in ["GOODYEAR", "DUNLOP", "YOKOHAMA", "HANKOOK"]):
        mult = 1.25
    else:
        mult = 1.0

    est = int(base * mult)
    return [
        {
            "source": "הערכה מקומית",
            "price":  est,
            "title":  f"מחיר משוער {tire_size} {brand} (ללא גישה לאינטרנט)",
            "url":    "",
        },
        {
            "source": "טווח שוק",
            "price":  int(est * 0.85),
            "title":  f"מחיר מינימום משוער",
            "url":    "",
        },
        {
            "source": "טווח שוק",
            "price":  int(est * 1.20),
            "title":  f"מחיר מקסימום משוער",
            "url":    "",
        },
    ]


def format_competitor_report(tire_size: str, brand: str, results: list) -> str:
    """מפרמט דו\"ח מחירי מתחרים"""
    title_line = f"מחירי שוק — {tire_size} {brand}".strip()
    lines = [title_line, "─" * 44]

    prices_found = [r["price"] for r in results if r.get("price")]

    if not prices_found:
        lines.append("לא נמצאו מחירים ספציפיים.")
        return "\n".join(lines)

    for r in results:
        price_str = f"{r['price']:,} ₪" if r.get("price") else "לא צוין"
        src       = (r.get("source") or "")[:28]
        lines.append(f"• {src:<28} {price_str:>10}")
        if r.get("title") and r["title"] != src:
            lines.append(f"  {r['title'][:60]}")

    lines += [
        "─" * 44,
        f"מחיר מינ':  {min(prices_found):,} ₪",
        f"מחיר מקס': {max(prices_found):,} ₪",
        f"ממוצע:      {int(sum(prices_found) / len(prices_found)):,} ₪",
    ]
    return "\n".join(lines)
