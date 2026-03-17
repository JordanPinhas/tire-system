"""
MarketingAgent - סוכן שיווק לעסק הצמיגים
אחראי על: פרסומות, מסעות שיווק, תוכן לרשתות חברתיות
"""

from agents.base_agent import BaseAgent


SYSTEM_PROMPT = """אתה סוכן שיווק מקצועי של חברת יבוא וסיטונאות צמיגים בישראל.
תפקידך לסייע בכל הנושאים השיווקיים:

- כתיבת פרסומות ותוכן שיווקי לפייסבוק, אינסטגרם ווואטסאפ
- יצירת מבצעים ומסעות פרסום לעונות שונות (חורף/קיץ)
- ניסוח הצעות ערך ומסרים ללקוחות מוסכים, צמיגיות וסיטונאים
- המלצות על אסטרטגיית שיווק ותמחור

הקהל שלך הוא בעלי מוסכים, בעלי צמיגיות ורוכשים סיטונאיים בישראל.
דבר בשפה עברית, ברורה, עסקית ומשכנעת.
כל תוכן שיווקי יהיה מותאם לשוק הישראלי."""


class MarketingAgent(BaseAgent):
    """סוכן שיווק - מייצר תוכן שיווקי לעסק הצמיגים"""

    def __init__(self):
        # מנסה לטעון פרומפט מקובץ, חוזר ל-fallback אם לא קיים
        try:
            system_prompt = self.load_prompt("marketing_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT

        super().__init__(name="סוכן שיווק", system_prompt=system_prompt)

    def run(self, user_input: str) -> str:
        """מעבד בקשה שיווקית ומחזיר תוכן מותאם"""
        return self.chat(user_input)

    def create_ad(self, platform: str, product: str, offer: str) -> str:
        """יוצר פרסומת מוכנה לפלטפורמה ספציפית"""
        prompt = (
            f"צור פרסומת ל{platform} עבור המוצר: {product}.\n"
            f"המבצע/הצעת הערך: {offer}.\n"
            "כלול: כותרת מושכת, גוף הפרסומת, קריאה לפעולה (CTA) וקצת אמוג'י."
        )
        return self.chat(prompt, keep_history=False)

    def create_seasonal_campaign(self, season: str) -> str:
        """יוצר מסע פרסום עונתי (חורף/קיץ)"""
        prompt = (
            f"צור מסע פרסום שלם לעונת ה{season} לעסק יבוא צמיגים.\n"
            "כלול: מסר מרכזי, 3 פוסטים לרשתות חברתיות, הצעת מבצע ספציפית."
        )
        return self.chat(prompt, keep_history=False)

    def create_campaign(self, topic: str, platforms: list,
                        campaign_type: str = "פוסט") -> dict:
        """
        יוצר קמפיין מלא:
        1. שיווק יוצר אסטרטגיה וקונספט
        2. קופירייטינג כותב טקסט לכל פלטפורמה
        3. Imagen יוצר תמונה
        4. שומר לתור אישורים
        """
        import json
        from datetime import datetime
        from pathlib import Path

        # שלב 1: אסטרטגיה מסוכן השיווק
        strategy = self.chat(
            f"צור קונספט קצר לקמפיין {campaign_type} בנושא: {topic}. "
            f"פלטפורמות: {', '.join(platforms)}. "
            "תן כותרת, מסר מרכזי, וקהל יעד. עד 5 שורות.",
            keep_history=False
        )

        # שלב 2: טקסטים מסוכן הקופירייטינג
        if self._agent_caller:
            texts_raw = self.ask_agent(
                "סוכן קופירייטינג",
                f"כתוב טקסטים לקמפיין:\n{strategy}\n\n"
                f"כתוב טקסט נפרד לכל פלטפורמה: {', '.join(platforms)}. "
                "פורמט: פלטפורמה: טקסט"
            )
        else:
            texts_raw = strategy

        # שלב 3: תמונה
        image_path = None
        try:
            from skills.image_generator import generate_marketing_image
            result = generate_marketing_image(
                prompt=(
                    f"Professional tire advertisement for Israeli market. "
                    f"Topic: {topic}. "
                    f"Campaign type: {campaign_type}. "
                    "Dark blue and orange colors, modern design, "
                    "NO TEXT in image, high quality commercial photo."
                ),
                aspect_ratio="1:1",
                model="imagen-4.0-generate-001",
            )
            if result.get("success"):
                image_path = result.get("path")
                print(f"[CAMPAIGN] תמונה נוצרה: {image_path}")
            else:
                image_path = None
                print(f"[CAMPAIGN] שגיאת תמונה: {result.get('error')}")
        except Exception as e:
            print(f"[CAMPAIGN] Exception בתמונה: {e}")
            image_path = None

        # שלב 4: שמור לתור אישורים
        queue_file = Path(__file__).parent.parent / "data" / "campaigns_queue.json"
        try:
            queue = json.loads(queue_file.read_text(encoding="utf-8"))
        except Exception:
            queue = []

        campaign = {
            "id": len(queue) + 1,
            "topic": topic,
            "campaign_type": campaign_type,
            "platforms": platforms,
            "strategy": strategy,
            "texts": texts_raw,
            "image_path": image_path,
            "image_base64": None,
            "status": "ממתין_לאישור",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "approved_at": None,
            "published_at": None,
            "rejected_reason": None,
        }

        if result.get("success") and result.get("path"):
            try:
                import base64
                with open(result["path"], "rb") as f:
                    campaign["image_base64"] = base64.b64encode(
                        f.read()).decode("utf-8")
            except Exception as e:
                print(f"[CAMPAIGN] base64 error: {e}")
                campaign["image_base64"] = None
        else:
            campaign["image_base64"] = None
        print(f"[CAMPAIGN] image_base64 length: {len(campaign.get('image_base64', '') or '')}")
        queue.append(campaign)
        queue_file.write_text(
            json.dumps(queue, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[CAMPAIGN CREATED] id={campaign['id']} topic={topic} status={campaign['status']}")
        print(f"[CAMPAIGN FILE] saved to {queue_file}")
        print(f"[CAMPAIGN FILE] exists={queue_file.exists()}")
        return campaign
