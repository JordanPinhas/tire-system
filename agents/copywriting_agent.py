"""
CopywritingAgent - סוכן קופירייטינג לעסק הצמיגים
אחראי על: תיאורי מוצר, מודעות ממומנות, סלוגנים, תסריטי מכירה
"""

from agents.base_agent import BaseAgent


SYSTEM_PROMPT_FALLBACK = """אתה קופירייטר מקצועי של חברת יבוא וסיטונאות צמיגים בישראל.
אתה מתמחה בכתיבה שיווקית ממירה: תיאורי מוצר, מודעות ממומנות, סלוגנים ותסריטי מכירה.
כתוב בעברית ברורה, ממוקדת תועלות, עם קריאה לפעולה חדה."""


class CopywritingAgent(BaseAgent):
    """סוכן קופירייטינג - יוצר תוכן כתוב ממיר לעסק הצמיגים"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("copywriting_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן קופירייטינג", system_prompt=system_prompt)

    def run(self, user_input: str) -> str:
        return self.chat(user_input)

    def write_product_description(self, brand: str, model: str, size: str, features: str) -> str:
        """כותב תיאור מוצר מלא לצמיג"""
        prompt = (
            f"כתוב תיאור מוצר מקצועי ומשכנע לצמיג הבא:\n"
            f"מותג: {brand}\n"
            f"דגם: {model}\n"
            f"מידה: {size}\n"
            f"תכונות עיקריות: {features}\n\n"
            "כלול: כותרת מושכת, פסקת פתיחה, 4-5 יתרונות בנקודות, ומשפט סגירה עם CTA."
        )
        return self.chat(prompt, keep_history=False)

    def write_google_ad(self, product: str, target_audience: str, usp: str) -> str:
        """כותב מודעת גוגל ממומנת (3 כותרות + 2 תיאורים)"""
        prompt = (
            f"כתוב מודעת Google Ads עבור:\n"
            f"מוצר: {product}\n"
            f"קהל יעד: {target_audience}\n"
            f"יתרון ייחודי (USP): {usp}\n\n"
            "פורמט נדרש:\n"
            "כותרת 1 (עד 30 תווים): ...\n"
            "כותרת 2 (עד 30 תווים): ...\n"
            "כותרת 3 (עד 30 תווים): ...\n"
            "תיאור 1 (עד 90 תווים): ...\n"
            "תיאור 2 (עד 90 תווים): ..."
        )
        return self.chat(prompt, keep_history=False)

    def write_facebook_ad(self, product: str, offer: str, audience: str) -> str:
        """כותב מודעת פייסבוק ממומנת"""
        prompt = (
            f"כתוב מודעת פייסבוק ממומנת עבור:\n"
            f"מוצר: {product}\n"
            f"מבצע/הצעה: {offer}\n"
            f"קהל: {audience}\n\n"
            "כלול: וו פתיחה מושך (שורה ראשונה), גוף טקסט (3-4 שורות), CTA ברור."
        )
        return self.chat(prompt, keep_history=False)

    def generate_slogans(self, brand_or_product: str, tone: str = "מקצועי ואמין") -> str:
        """מייצר 5 סלוגן אפשריים"""
        prompt = (
            f"צור 5 סלוגנים לעסק/מוצר: {brand_or_product}\n"
            f"טון: {tone}\n"
            "כל סלוגן: קצר (עד 7 מילים), בולט, נזכר, בעברית."
        )
        return self.chat(prompt, keep_history=False)

    def write_sales_script(self, customer_type: str, product: str, objection: str = "") -> str:
        """כותב תסריט שיחת מכירה"""
        prompt = (
            f"כתוב תסריט שיחת מכירה עבור:\n"
            f"סוג לקוח: {customer_type}\n"
            f"מוצר: {product}\n"
        )
        if objection:
            prompt += f"התנגדות עיקרית לטפל בה: {objection}\n"
        prompt += (
            "\nכלול: פתיחת שיחה, 3 שאלות גילוי צורך, הצגת הפתרון, "
            "טיפול בהתנגדות, וסגירה."
        )
        return self.chat(prompt, keep_history=False)
