"""
route_calculator.py — מציאת נקודת שירות קרובה וחישוב מרחק
(ללא API חיצוני — חישוב לוקאלי לפי קואורדינטות)
"""

import json
import math
import re
from pathlib import Path

SERVICE_POINTS_FILE = Path(__file__).parent.parent / "data" / "service_points.json"

# קואורדינטות ערים ישראליות עיקריות
CITY_COORDS = {
    "תל אביב":     (32.0853, 34.7818),
    "יפו":         (32.0551, 34.7535),
    "ירושלים":     (31.7683, 35.2137),
    "חיפה":        (32.8191, 34.9983),
    "באר שבע":     (31.2518, 34.7913),
    "נתניה":       (32.3215, 34.8533),
    "פתח תקווה":   (32.0878, 34.8878),
    "ראשון לציון": (31.9730, 34.7925),
    "אשדוד":       (31.8040, 34.6550),
    "אשקלון":      (31.6690, 34.5706),
    "רחובות":      (31.8956, 34.8115),
    "הרצליה":      (32.1663, 34.8431),
    "כפר סבא":     (32.1753, 34.9077),
    "הוד השרון":   (32.1521, 34.8941),
    "רמת גן":      (32.0686, 34.8238),
    "גבעתיים":     (32.0710, 34.8137),
    "חולון":       (32.0110, 34.7796),
    "בת ים":       (32.0211, 34.7506),
    "לוד":         (31.9519, 34.8938),
    "רמלה":        (31.9298, 34.8712),
    "מודיעין":     (31.8969, 35.0095),
    "מודיעין עילית": (31.9318, 35.0436),
    "נצרת":        (32.6996, 35.3035),
    "עכו":         (32.9203, 35.0696),
    "טבריה":       (32.7940, 35.5300),
    "צפת":         (32.9647, 35.4950),
    "נהריה":       (33.0049, 35.0963),
    "אילת":        (29.5577, 34.9519),
    "עפולה":       (32.6078, 35.2897),
    "כרמיאל":      (32.9187, 35.2961),
    "טירת כרמל":   (32.7636, 34.9699),
    "קריית שמונה": (33.2074, 35.5706),
    "דימונה":      (31.0696, 35.0326),
    "קריית גת":    (31.6100, 34.7642),
    "רהט":         (31.3927, 34.7540),
    "קריית אתא":   (32.8041, 35.1100),
    "קריית ביאליק": (32.8341, 35.0787),
    "קריית מוצקין": (32.8366, 35.0726),
    "קריית ים":    (32.8534, 35.0679),
    "בני ברק":     (32.0841, 34.8337),
    "אור יהודה":   (32.0261, 34.8567),
    "יהוד":        (32.0311, 34.8881),
    "אלעד":        (32.0537, 34.9536),
    "טייבה":       (32.2693, 35.0008),
    "אום אל פאחם": (32.5161, 35.1523),
    "שפרעם":       (32.8053, 35.1659),
    "מעלה אדומים": (31.7771, 35.3029),
    "ביתר עילית":  (31.6937, 35.1115),
    "בית שמש":     (31.7487, 34.9903),
    "קרית מלאכי":  (31.7292, 34.7389),
    "מגדל העמק":   (32.6786, 35.2398),
}


def get_all_service_points() -> list:
    """מחזיר רשימת כל נקודות השירות"""
    try:
        if SERVICE_POINTS_FILE.exists():
            data = json.loads(SERVICE_POINTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    # ברירת מחדל — שני סניפים עיקריים
    return [
        {"id": "SP001", "name": "סניף צפון - חיפה", "address": "רחוב התעשייה 12, חיפה",
         "phone": "04-8000001", "lat": 32.8191, "lon": 34.9983, "type": "own",
         "hours": "א-ה 08:00-18:00", "services": ["החלפת צמיגים", "תיקון פנצ'ר"]},
        {"id": "SP002", "name": "סניף מרכז - פתח תקווה", "address": "רחוב הרכב 7, פתח תקווה",
         "phone": "03-9000001", "lat": 32.0878, "lon": 34.8878, "type": "own",
         "hours": "א-ה 08:00-19:00", "services": ["החלפת צמיגים", "תיקון פנצ'ר", "אחסון עונתי"]},
    ]


def find_nearest_service_point(address: str, service_type: str = "") -> dict:
    """
    מוצא נקודת שירות קרובה ביותר לכתובת.
    address: עיר או כתובת בעברית
    service_type: סינון לפי שירות (אופציונלי)
    """
    points = get_all_service_points()

    if service_type:
        filtered = [p for p in points if service_type in p.get("services", [])]
        if filtered:
            points = filtered

    origin = _geocode(address)
    if not origin:
        return {**points[0], "distance_km": None, "note": "לא ניתן לחשב מרחק — עיר לא זוהתה"}

    results = _sort_by_distance(points, origin)
    return results[0]


def get_nearest_sorted(address: str, limit: int = 5) -> list:
    """רשימת נקודות שירות ממוינת לפי מרחק מהכתובת"""
    points = get_all_service_points()
    origin = _geocode(address)
    if not origin:
        return [{**p, "distance_km": None} for p in points[:limit]]
    return _sort_by_distance(points, origin)[:limit]


def calculate_route(origin: str, destination: str) -> dict:
    """
    מחשב מרחק משוער בין שתי כתובות.
    מחזיר: {"distance_km", "duration_min", "origin", "destination"}
    """
    o = _geocode(origin)
    d = _geocode(destination)

    if not o or not d:
        missing = origin if not o else destination
        return {
            "origin": origin, "destination": destination,
            "distance_km": None, "duration_min": None,
            "note": f"לא ניתן לחשב — '{missing}' לא זוהתה",
        }

    dist     = _haversine(o[0], o[1], d[0], d[1])
    duration = int(dist / 60 * 60)  # ~60 קמ"ש ממוצע

    return {
        "origin":       origin,
        "destination":  destination,
        "distance_km":  round(dist, 1),
        "duration_min": duration,
        "note":         "מרחק כביש משוער (מבוסס קואורדינטות)",
    }


def format_service_point(p: dict, show_distance: bool = True) -> str:
    """פורמט נקודת שירות לתצוגה"""
    type_label = "🏢 בבעלות" if p.get("type") == "own" else "🤝 שותף"
    dist_str   = f" | {p['distance_km']} ק\"מ" if show_distance and p.get("distance_km") is not None else ""
    services   = ", ".join(p.get("services", []))
    return (
        f"{type_label} — {p['name']}{dist_str}\n"
        f"  📍 {p['address']}\n"
        f"  📞 {p['phone']}\n"
        f"  🕐 {p.get('hours', '')}\n"
        f"  🔧 {services}"
    )


def format_nearest_points(address: str, limit: int = 3) -> str:
    """טקסט מסודר של נקודות הקרובות ביותר לכתובת"""
    points = get_nearest_sorted(address, limit)
    if not points:
        return "לא נמצאו נקודות שירות."

    lines = [f"נקודות שירות קרובות ל-{address}:", ""]
    for i, p in enumerate(points, 1):
        lines.append(f"{i}. {format_service_point(p)}")
        lines.append("")
    return "\n".join(lines).strip()


# ── עזר ────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """מרחק כביש משוער בק\"מ (haversine × 1.25 לחישוב דרכים)"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    c    = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.25


def _geocode(address: str) -> tuple:
    """מחזיר (lat, lon) לכתובת עברית — חיפוש לפי שם עיר"""
    if not address:
        return None
    addr = address.strip()

    # חיפוש שם עיר מדויק
    for city, coords in CITY_COORDS.items():
        if city in addr:
            return coords

    # חיפוש חלקי (שתי אותיות ראשונות)
    addr_lower = addr.lower()
    for city, coords in CITY_COORDS.items():
        if city[:3] in addr:
            return coords

    # מספרי קואורדינטות ישירות
    m = re.search(r"(3[01234]\.\d+)[,\s]+(3[34567]\.\d+)", addr)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None


def _sort_by_distance(points: list, origin: tuple) -> list:
    result = []
    for p in points:
        lat, lon = p.get("lat", 0), p.get("lon", 0)
        dist = _haversine(origin[0], origin[1], lat, lon)
        result.append({**p, "distance_km": round(dist, 1)})
    result.sort(key=lambda x: x["distance_km"])
    return result
