# מערכת סוכני AI - עסק צמיגים

## תיאור הפרויקט
מערכת Python מרובת סוכני AI לניהול עסק יבוא ושיווק צמיגים.
8 סוכנים המתקשרים דרך Orchestrator מרכזי עם ניתוב חכם (מילות מפתח + AI fallback).
שפת עבודה: עברית (ממשק) + Python (קוד).

## Stack טכנולוגי
- Python 3.11
- Anthropic SDK (claude-sonnet-4-5)
- JSON files for data storage
- python-dotenv for env management

## כללי פיתוח
1. כל agent יורש מ-BaseAgent ב-agents/base_agent.py
2. כל skill הוא פונקציה עצמאית ב-skills/
3. system prompts שמורים בקבצי .txt ב-prompts/
4. נתונים שמורים ב-JSON ב-data/
5. לעולם אל תכתוב API key בקוד - תמיד דרך .env

## סוכנים פעילים (8/8)

| סוכן | קובץ | אחריות עיקרית |
|------|------|--------------|
| סוכן שיווק | agents/marketing_agent.py | פרסומות, קמפיינים עונתיים, רשתות חברתיות |
| סוכן קופירייטינג | agents/copywriting_agent.py | תיאורי מוצר, מודעות גוגל/פייסבוק, סלוגנים, תסריטים |
| סוכן מכירות | agents/sales_agent.py | הצעות מחיר, ניהול לידים (data/leads.json) |
| סוכן מלאי | agents/inventory_agent.py | מלאי (data/inventory.json), חיפוש מידה, התראות |
| סוכן שירות | agents/service_agent.py | תורים (data/appointments.json), 2 סניפים + 30 חיצוניים |
| סוכן תמחור | agents/pricing_agent.py | מרג'ין לפי סוג לקוח, חישוב מקומי + AI, פנצ'ר |
| סוכן תמיכה | agents/support_agent.py | בחירת צמיג, FAQ, ייעוץ תחזוקה, תלונות |
| סוכן דוחות | agents/reporting_agent.py | דוחות מלאי/לידים/תורים, סיכום יומי |

## Orchestrator - ניתוב דו-שלבי
1. **מהיר**: ROUTING_RULES - מילות מפתח לפי עדיפות
2. **AI fallback**: כשאין התאמה — שואל Claude איזה סוכן מתאים (max_tokens=30)

## קבצי נתונים
- `data/leads.json` — לידים (id, name, phone, customer_type, status)
- `data/inventory.json` — מלאי (id, brand, model, size, quantity, cost_price, min_qty)
- `data/appointments.json` — תורים (id, customer_name, date, time, location, service_type, status)

## הרצה
```bash
pip install -r requirements.txt
cp .env.example .env   # הוסף: ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

## פקודות CLI (גרסה 4.0)
שיווק: /פרסומת /עונה /קופי
מכירות: /מכירה /ציי /ליד /לידים
מלאי: /מלאי /הוסף /חפש
שירות: /תור /תורים /סניפים
תמחור: /מחיר /פנצ'ר
תמיכה: /תמיכה /faq
דוחות: /דוח /סיכום
