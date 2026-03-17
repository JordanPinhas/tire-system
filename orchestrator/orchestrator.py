"""
Orchestrator - המנהל המרכזי של כל הסוכנים
שלב 1: ניתוב מהיר לפי מילות מפתח
שלב 2 (fallback): ניתוב חכם דרך Claude
"""

import os
import anthropic
from dotenv import load_dotenv
from agents.base_agent import BaseAgent

load_dotenv()

# מילות מפתח לניתוב מהיר (סדר = עדיפות)
ROUTING_RULES: list[tuple[list[str], str]] = [
    (
        ["מלאי", "כמות במלאי", "מידה", "פריט", "מוצר במלאי",
         "מלאי נמוך", "חיפוש צמיג", "זמינות"],
        "סוכן מלאי",
    ),
    (
        ["תור", "תורים", "קביעת תור", "נקודת שירות", "התקנה", "פנצ'ר",
         "איזון", "עיצוב גלגל", "אחסון עונתי", "סניף"],
        "סוכן שירות",
    ),
    (
        ["תמחור", "מרג'ין", "רווח", "עלות", "חישוב מחיר", "מחיר שוק",
         "הנחת כמות", "תעריף", "מחיר פנצ'ר"],
        "סוכן תמחור",
    ),
    (
        ["תסריט", "סלוגן", "תיאור מוצר", "מודעת גוגל", "מודעת פייסבוק",
         "קופי", "כותרת", "טקסט פרסומי", "תוכן כתוב", "מודעה ממומנת"],
        "סוכן קופירייטינג",
    ),
    (
        ["הצעת מחיר", "ליד", "לקוח פוטנציאלי", "ציי רכב",
         "חוזה", "סגירה", "התנגדות", "אשראי"],
        "סוכן מכירות",
    ),
    (
        ["דוח", "סיכום", "אנליטיקה", "ניתוח נתונים", "דוחות",
         "ביצועים", "סטטיסטיקה", "כמה לידים", "כמה תורים"],
        "סוכן דוחות",
    ),
    (
        ["תלונה", "בעיה עם", "לא מרוצה", "ייעוץ בחירה", "איזה צמיג",
         "בטיחות", "תחזוקה", "לחץ אוויר", "עומק חריץ", "גיל צמיג",
         "שאלה על", "faq", "שאלות נפוצות"],
        "סוכן תמיכה",
    ),
    (
        ["פרסומת", "פרסום", "שיווק", "מבצע", "קמפיין", "פוסט",
         "פייסבוק", "אינסטגרם", "וואטסאפ", "מסר", "עונת", "קהל"],
        "סוכן שיווק",
    ),
    (
        ["rely", "ריל", "פוליאוריתן", "מילוי צמיג", "puncture proof",
         "t-25", "t25", "carpenter", "חבית rely", "מילוי מלגזה"],
        "סוכן Rely",
    ),
]

DEFAULT_AGENT = "סוכן תמיכה"

# תיאור קצר של כל סוכן לשימוש בניתוב AI
AGENT_DESCRIPTIONS = {
    "סוכן Rely":        "מילוי פוליאוריתן Rely®, חישוב כמות חומר, T-25, T-25 OEM, מלגזות",
    "סוכן מלאי":        "ניהול וצפייה במלאי צמיגים, חיפוש לפי מידה, התראות מלאי נמוך",
    "סוכן שירות":       "קביעת תורים, ניהול עבודות שירות, נקודות שירות",
    "סוכן תמחור":       "חישוב מחיר מכירה, מרג'ין, השוואת שוק, תמחור פנצ'ר",
    "סוכן קופירייטינג": "כתיבת תיאורי מוצר, מודעות, סלוגנים, תסריטי מכירה",
    "סוכן מכירות":      "הצעות מחיר, ניהול לידים, מכירות B2B",
    "סוכן שיווק":       "קמפיינים, פרסומות, תוכן לרשתות חברתיות",
    "סוכן תמיכה":       "ייעוץ ללקוחות, בחירת צמיג, FAQ, תלונות",
    "סוכן דוחות":       "דוחות מלאי, לידים, תורים, סיכום יומי",
}

ROUTER_SYSTEM_PROMPT = """אתה מנתב בקשות לסוכן AI המתאים ביותר.
ענה רק בשם הסוכן, ללא הסברים נוספים."""


class Orchestrator:
    """מנהל מרכזי עם ניתוב דו-שלבי: מילות מפתח → AI"""

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self._router_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._load_agents()
        self._connect_agents()

    def _load_agents(self):
        """טוען את כל 9 הסוכנים"""
        from agents.marketing_agent import MarketingAgent
        from agents.copywriting_agent import CopywritingAgent
        from agents.sales_agent import SalesAgent
        from agents.inventory_agent import InventoryAgent
        from agents.service_agent import ServiceAgent
        from agents.pricing_agent import PricingAgent
        from agents.support_agent import SupportAgent
        from agents.reporting_agent import ReportingAgent
        from agents.rely_agent import RelyAgent

        for agent in [
            MarketingAgent(), CopywritingAgent(), SalesAgent(),
            InventoryAgent(), ServiceAgent(), PricingAgent(),
            SupportAgent(), ReportingAgent(), RelyAgent(),
        ]:
            self.agents[agent.name] = agent

    def _connect_agents(self):
        """מחבר את כל הסוכנים אחד לשני"""
        for agent in self.agents.values():
            agent._agent_caller = self._call_agent

    def _call_agent(self, agent_name: str, query: str) -> str:
        """נקרא על ידי סוכן כשהוא רוצה מידע מסוכן אחר"""
        target = self.agents.get(agent_name)
        if not target:
            return f"[סוכן '{agent_name}' לא נמצא]"
        return target.run(query)

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent
        agent._agent_caller = self._call_agent

    def route(self, user_input: str) -> tuple[str, str]:
        """מנתב ומחזיר (שם_סוכן, תשובה)"""
        agent = self._pick_agent(user_input)
        response = agent.run(user_input)
        return agent.name, response

    def _pick_agent(self, user_input: str) -> BaseAgent:
        """שלב 1: מילות מפתח. שלב 2: AI router."""
        # ניתוב מהיר
        for keywords, agent_name in ROUTING_RULES:
            for keyword in keywords:
                if keyword in user_input:
                    agent = self.agents.get(agent_name)
                    if agent:
                        return agent

        # fallback: שואל את Claude
        return self._ai_route(user_input)

    def _ai_route(self, user_input: str) -> BaseAgent:
        """ניתוב חכם: שולח ל-Claude שיחליט מי מטפל"""
        agents_list = "\n".join(
            f"- {name}: {desc}"
            for name, desc in AGENT_DESCRIPTIONS.items()
            if name in self.agents
        )
        user_prompt = (
            f"סוכנים זמינים:\n{agents_list}\n\n"
            f"בקשת המשתמש: {user_input}\n\n"
            "איזה סוכן מתאים ביותר? ענה רק בשם הסוכן."
        )
        try:
            response = self._router_client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=30,
                system=ROUTER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            chosen = response.content[0].text.strip()
            agent = self.agents.get(chosen)
            if agent:
                return agent
        except Exception:
            pass

        return self.agents[DEFAULT_AGENT]

    def list_agents(self) -> list[str]:
        return list(self.agents.keys())
