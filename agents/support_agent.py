"""
SupportAgent - סוכן תמיכה ושירות לקוחות
אחראי על: בחירת צמיג, FAQ, ייעוץ תחזוקה, טיפול בתלונות
"""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT_FALLBACK = """אתה סוכן תמיכה ושירות לקוחות של חברת יבוא צמיגים בישראל.
מומחה בבחירת צמיגים, בטיחות ותחזוקה. דבר בחמימות ובוודאות, בעברית נגישה."""

# שאלות נפוצות מוכנות מראש (ללא שיחת API)
FAQ_ANSWERS: dict[str, str] = {
    "לחץ": "לחץ אוויר מומלץ מצוין בדלת הנהג או במדריך הרכב. בדוק אחת לחודש ולפני נסיעה ארוכה.",
    "עומק חריץ": "עומק מינימלי חוקי: 1.6 מ\"מ. מומלץ להחליף ב-3 מ\"מ. מטבע 10 אגורות = בדיקה פשוטה.",
    "גיל צמיג": "צמיג ישן מ-6 שנים מומלץ להחלפה, גם אם נראה תקין. תאריך ייצור = 4 ספרות בצד (שבוע/שנה).",
    "פנצ'ר": "צמיג שנפנצ'ר ניתן לתיקון אם הנזק בחלק האמצעי ועד 6 מ\"מ. בצד הצמיג — בדרך כלל לא ניתן לתיקון.",
    "החלפת עונה": "בישראל: צמיגי חורף מומלצים לגליל/גולן בחודשים נובמבר-מרץ. בשאר הארץ — צמיגים כל-עונה מספיקים.",
    "TPMS": "מערכת TPMS מתריעה על לחץ נמוך. אחרי מילוי אוויר — אפס את המערכת לפי מדריך הרכב.",
}


class SupportAgent(BaseAgent):
    """סוכן תמיכה - ייעוץ לקוחות ושאלות נפוצות"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("support_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן תמיכה", system_prompt=system_prompt)

    def run(self, user_input: str) -> str:
        return self.chat(user_input)

    def tire_selection_guide(self, vehicle: str, budget: str,
                             season: str, usage: str = "עירוני") -> str:
        """מדריך בחירת צמיג מותאם אישית"""
        prompt = (
            f"עזור ללקוח לבחור צמיגים:\n"
            f"רכב: {vehicle}\n"
            f"תקציב: {budget}\n"
            f"עונה/תנאים: {season}\n"
            f"סוג שימוש: {usage}\n\n"
            "הצג 3 אפשרויות (בסיסי / ביצועים / פרמיום):\n"
            "לכל אפשרות: מותג מומלץ, מה היתרון, למי מתאים, טווח מחיר.\n"
            "הוסף: טיפ חשוב אחד לבטיחות."
        )
        return self.chat(prompt, keep_history=True)

    def answer_faq(self, question: str) -> str:
        """עונה לשאלה נפוצה - קודם בודק תשובה מוכנה, אחרת שולח ל-AI"""
        for keyword, answer in FAQ_ANSWERS.items():
            if keyword in question:
                return f"[תשובה מהירה]\n{answer}"
        # שאלה שאינה בבסיס הידע - שולח ל-Claude
        return self.chat(question, keep_history=False)

    def maintenance_advice(self, tire_age_years: float,
                           mileage_km: int, condition_desc: str) -> str:
        """ייעוץ תחזוקה לפי גיל, קילומטראז' ומצב"""
        urgency = "דחוף" if tire_age_years >= 6 or mileage_km >= 60000 else "שוטף"
        prompt = (
            f"ספק ייעוץ תחזוקת צמיגים:\n"
            f"גיל הצמיגים: {tire_age_years} שנים\n"
            f"קילומטראז': {mileage_km:,} ק\"מ\n"
            f"מצב מתואר: {condition_desc}\n"
            f"רמת דחיפות להערכה: {urgency}\n\n"
            "כלול: האם להחליף עכשיו? מה לבדוק? מה מרווח הזמן? המלצה פרקטית."
        )
        return self.chat(prompt, keep_history=False)

    def handle_complaint(self, complaint_type: str, details: str) -> str:
        """טיפול בתלונת לקוח — אמפטיה + פתרון"""
        prompt = (
            f"לקוח הגיש תלונה:\n"
            f"סוג תלונה: {complaint_type}\n"
            f"פרטים: {details}\n\n"
            "כתוב תגובה מקצועית הכוללת:\n"
            "1. הכרה בבעיה ואמפטיה\n"
            "2. התנצלות כנה על אי-הנוחות\n"
            "3. פתרון קונקרטי עם ציר זמן\n"
            "4. הצעת פיצוי/מחווה אם מתאים\n"
            "5. קריאה לפעולה ברורה (איך הלקוח מתקדם)"
        )
        return self.chat(prompt, keep_history=False)

    def list_faq_topics(self) -> str:
        """מחזיר רשימת נושאי FAQ זמינים"""
        topics = list(FAQ_ANSWERS.keys())
        return "נושאי FAQ זמינים:\n" + "\n".join(f"  • {t}" for t in topics)
