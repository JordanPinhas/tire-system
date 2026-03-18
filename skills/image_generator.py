"""
image_generator.py — יצירת תמונות שיווקיות עם Google Imagen 4 / Gemini
מבוסס על תיעוד רשמי של Google AI Studio
"""

import mimetypes
import os
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

PERSISTENT_DIR = Path("/opt/render/project/src/persistent")
if not PERSISTENT_DIR.exists():
    PERSISTENT_DIR = Path(__file__).parent.parent
MARKETING_DIR = PERSISTENT_DIR / "outputs" / "marketing"
MARKETING_DIR.mkdir(parents=True, exist_ok=True)


def get_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return genai.Client(api_key=api_key)


def generate_with_gemini(
    prompt: str,
    aspect_ratio: str = "1:1",
    model: str = "gemini-2.5-flash-image",
) -> dict:
    """יצירה עם Nano Banana / Gemini Image — לפי תיעוד רשמי"""
    client = get_client()
    MARKETING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
            filename = f"img_{timestamp}{ext}"
            out_path = MARKETING_DIR / filename
            with open(str(out_path), "wb") as f:
                f.write(part.inline_data.data)
            return {
                "success":   True,
                "path":      str(out_path),
                "filename":  filename,
                "timestamp": timestamp,
                "model":     model,
            }

    return {"success": False, "error": "לא נוצרה תמונה — נסה שנית"}


def generate_with_imagen(
    prompt: str,
    aspect_ratio: str = "1:1",
    model: str = "imagen-4.0-generate-001",
) -> dict:
    """יצירה עם Imagen 4"""
    client = get_client()
    MARKETING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    ratio_map = {"1:1": "1:1", "16:9": "16:9", "9:16": "9:16", "4:3": "4:3", "3:4": "3:4"}
    imagen_ratio = ratio_map.get(aspect_ratio, "1:1")

    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=imagen_ratio,
        ),
    )

    if response.generated_images:
        filename = f"img_{timestamp}.png"
        out_path = MARKETING_DIR / filename
        with open(str(out_path), "wb") as f:
            f.write(response.generated_images[0].image.image_bytes)
        return {
            "success":   True,
            "path":      str(out_path),
            "filename":  filename,
            "timestamp": timestamp,
            "model":     model,
        }

    return {"success": False, "error": "לא נוצרה תמונה — נסה שנית"}


def generate_marketing_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    model: str = "imagen-4.0-generate-001",
) -> dict:
    """פונקציה ראשית — בוחרת אוטומטית בין Imagen ל-Gemini לפי שם המודל"""
    print(f"[IMAGE GEN] model={model}, aspect={aspect_ratio}")
    print(f"[IMAGE GEN] prompt={prompt[:80]}...")
    try:
        if "imagen" in model:
            result = generate_with_imagen(prompt, aspect_ratio, model)
        else:
            result = generate_with_gemini(prompt, aspect_ratio, model)
        print(f"[IMAGE GEN] result={result}")
        return result
    except Exception as e:
        print(f"[IMAGE GEN] ERROR: {e}")
        error = str(e)
        if "RESOURCE_EXHAUSTED" in error or "429" in error:
            return {"success": False, "error": "⚠️ חרגת ממכסה. נסה מודל אחר או המתן."}
        if "404" in error:
            return {"success": False, "error": "❌ מודל לא זמין. נסה מודל אחר."}
        if "billing" in error.lower() or "paid" in error.lower():
            return {"success": False, "error": "💳 נדרש חיוב ב-Google AI Studio."}
        return {"success": False, "error": f"❌ {error[:200]}"}


def generate_flyer(
    title: str,
    subtitle: str,
    offer: str,
    phone: str,
    style: str = "מודרני",
) -> dict:
    """יוצר פלייר מלא — משתמש ב-Imagen 4 Ultra"""
    prompt = (
        f"Professional marketing flyer for Israeli tire company.\n"
        f"Title in Hebrew: {title}\n"
        f"Subtitle in Hebrew: {subtitle}\n"
        f"Special offer in Hebrew: {offer}\n"
        f"Phone: {phone}\n"
        f"Style: {style}, dark blue and orange colors, modern design, Hebrew text"
    )
    return generate_marketing_image(prompt, aspect_ratio="1:1", model="imagen-4.0-ultra-generate-001")


def generate_social_post(platform: str, message: str) -> dict:
    """יוצר תמונה מותאמת לרשת חברתית"""
    ratios = {
        "instagram": "1:1",
        "story":     "9:16",
        "facebook":  "16:9",
        "banner":    "16:9",
    }
    ratio = ratios.get(platform.lower(), "1:1")
    prompt = (
        f"Professional social media ad for Israeli tire company.\n"
        f"Platform: {platform}\n"
        f"Message in Hebrew: {message}\n"
        f"Style: Modern, dark blue and orange colors, Hebrew text"
    )
    return generate_marketing_image(prompt, aspect_ratio=ratio, model="imagen-4.0-generate-001")


def generate_marketing_image_no_text(
    description: str,
    aspect_ratio: str = "1:1",
    model: str = "imagen-4.0-generate-001",
) -> dict:
    """שלב 1 — יוצר תמונה ויזואלית ללא טקסט (מוכנה לשכבת טקסט עברי)"""
    prompt = (
        "Professional marketing image for tire company. "
        "ABSOLUTELY NO TEXT, NO WORDS, NO LETTERS, NO NUMBERS anywhere in the image. "
        f"Visual only: {description}. "
        "Style: dark blue and orange colors, modern professional design, high quality photography"
    )
    return generate_marketing_image(prompt=prompt, aspect_ratio=aspect_ratio, model=model)


def add_hebrew_text(image_path: str, texts: list) -> str:
    """
    שלב 2 — מוסיף טקסט עברי על התמונה עם Pillow + bidi
    texts = [
      {"text": "מבצע חורף", "x": 0.5, "y": 0.3, "size": 60, "color": "white"},
      {"text": "315/80R22.5",  "x": 0.5, "y": 0.5, "size": 48, "color": "#FF6B00"},
      {"text": "משלוח חינם",   "x": 0.5, "y": 0.7, "size": 36, "color": "white"},
    ]
    x, y — אחוזים מגודל התמונה (0.5 = מרכז)
    מחזיר את הנתיב לקובץ החדש עם _text בשם
    """
    from PIL import Image, ImageDraw, ImageFont
    from bidi.algorithm import get_display
    import arabic_reshaper

    FONT_CANDIDATES = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size

    for item in texts:
        text = item.get("text", "").strip()
        if not text:
            continue

        size  = item.get("size", 40)
        color = item.get("color", "white")

        # מציאת פונט
        font = None
        for fp in FONT_CANDIDATES:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, size)
                    break
                except Exception:
                    pass
        if font is None:
            font = ImageFont.load_default()

        # עיבוד עברית + bidi
        reshaped     = arabic_reshaper.reshape(text)
        display_text = get_display(reshaped)

        x = int(item.get("x", 0.5) * width)
        y = int(item.get("y", 0.5) * height)

        # צל
        draw.text((x + 2, y + 2), display_text, font=font, fill=(0, 0, 0, 200), anchor="mm")
        # טקסט ראשי
        draw.text((x, y), display_text, font=font, fill=color, anchor="mm")

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    p = Path(image_path)
    out_path = p.parent / f"{p.stem}_text{p.suffix}"
    combined.save(str(out_path))
    print(f"[TEXT OVERLAY] saved → {out_path}")
    return str(out_path)


def get_gallery() -> list:
    """מחזיר רשימת תמונות שנוצרו, מהחדש לישן"""
    if not MARKETING_DIR.exists():
        return []
    files = sorted(
        [f for f in MARKETING_DIR.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "filename": f.name,
            "size_kb":  round(f.stat().st_size / 1024),
            "created":  datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        }
        for f in files
    ]
