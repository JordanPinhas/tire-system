"""
מערכת סוכני AI - עסק צמיגים
ממשק שורת פקודה בעברית
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

BANNER = """
╔══════════════════════════════════════════════════╗
║       מערכת סוכני AI - עסק יבוא צמיגים          ║
║           גרסה 4.0 - מערכת מלאה (8 סוכנים)      ║
╚══════════════════════════════════════════════════╝
"""

MENU = """
פקודות זמינות:
  /סוכנים   - הצג סוכנים פעילים

  --- שיווק וקופי ---
  /פרסומת   - צור פרסומת שיווקית
  /עונה     - צור קמפיין עונתי
  /קופי     - אשף קופירייטינג

  --- מכירות ---
  /מכירה    - צור הצעת מחיר
  /ציי      - הצעת מחיר לציי רכב
  /ליד      - הוסף ליד חדש
  /לידים    - הצג לידים קיימים

  --- מלאי ---
  /מלאי     - הצג מלאי
  /הוסף     - הוסף/עדכן פריט במלאי
  /חפש      - חפש צמיג לפי מידה

  --- שירות ---
  /תור      - קבע תור חדש
  /תורים    - הצג תורים
  /סניפים   - פרטי נקודות שירות

  --- תמחור ---
  /מחיר     - חשב מחיר מכירה
  /פנצ'ר    - הצעת מחיר פנצ'ר

  --- תמיכה ---
  /תמיכה    - ייעוץ ובחירת צמיג ללקוח
  /faq      - שאלות נפוצות

  --- דוחות ---
  /דוח      - תפריט דוחות
  /סיכום    - סיכום יומי של העסק

  /נקה      - נקה היסטוריית שיחה
  /עזרה     - הצג תפריט זה
  /יציאה    - סיום

או פשוט כתוב שאלה/בקשה חופשית...
"""


def check_api_key():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("שגיאה: לא נמצא ANTHROPIC_API_KEY")
        print("צור קובץ .env עם: ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)


# --- אשפים ---

def handle_ad_wizard(orchestrator):
    """אשף יצירת פרסומת שיווקית"""
    print("\n--- אשף פרסומת ---")
    platform = input("פלטפורמה (פייסבוק/אינסטגרם/וואטסאפ): ").strip()
    product = input("מוצר/סוג צמיג: ").strip()
    offer = input("מבצע/הצעת ערך: ").strip()

    if not all([platform, product, offer]):
        print("בוטל - יש למלא את כל השדות.")
        return

    print("\nמייצר פרסומת...\n")
    from agents.marketing_agent import MarketingAgent
    agent = orchestrator.agents.get("סוכן שיווק")
    if isinstance(agent, MarketingAgent):
        result = agent.create_ad(platform, product, offer)
    else:
        _, result = orchestrator.route(f"צור פרסומת ל{platform} עבור {product} עם מבצע: {offer}")
    print(f"פרסומת:\n{result}\n")


def handle_season_campaign(orchestrator):
    """אשף קמפיין עונתי"""
    print("\n--- קמפיין עונתי ---")
    season = input("עונה (חורף/קיץ/אביב/סתיו): ").strip()
    if not season:
        print("בוטל.")
        return

    print(f"\nבונה קמפיין לעונת ה{season}...\n")
    from agents.marketing_agent import MarketingAgent
    agent = orchestrator.agents.get("סוכן שיווק")
    if isinstance(agent, MarketingAgent):
        result = agent.create_seasonal_campaign(season)
    else:
        _, result = orchestrator.route(f"צור קמפיין עונתי לעונת ה{season}")
    print(f"קמפיין עונתי:\n{result}\n")


def handle_copy_wizard(orchestrator):
    """אשף קופירייטינג"""
    from agents.copywriting_agent import CopywritingAgent
    agent = orchestrator.agents.get("סוכן קופירייטינג")

    print("\n--- אשף קופירייטינג ---")
    print("בחר סוג תוכן:")
    print("  1. תיאור מוצר")
    print("  2. מודעת גוגל")
    print("  3. מודעת פייסבוק")
    print("  4. סלוגנים")
    print("  5. תסריט מכירה")

    choice = input("בחירה (1-5): ").strip()

    if choice == "1":
        brand = input("מותג: ").strip()
        model = input("דגם: ").strip()
        size = input("מידה: ").strip()
        features = input("תכונות עיקריות: ").strip()
        if not all([brand, model, size, features]):
            print("בוטל.")
            return
        print("\nכותב תיאור מוצר...\n")
        result = agent.write_product_description(brand, model, size, features) if isinstance(agent, CopywritingAgent) \
            else orchestrator.route(f"כתוב תיאור מוצר לצמיג {brand} {model} {size}")[1]

    elif choice == "2":
        product = input("מוצר: ").strip()
        audience = input("קהל יעד: ").strip()
        usp = input("יתרון ייחודי (USP): ").strip()
        if not all([product, audience, usp]):
            print("בוטל.")
            return
        print("\nכותב מודעת גוגל...\n")
        result = agent.write_google_ad(product, audience, usp) if isinstance(agent, CopywritingAgent) \
            else orchestrator.route(f"כתוב מודעת גוגל עבור {product}")[1]

    elif choice == "3":
        product = input("מוצר: ").strip()
        offer = input("הצעה/מבצע: ").strip()
        audience = input("קהל יעד: ").strip()
        if not all([product, offer, audience]):
            print("בוטל.")
            return
        print("\nכותב מודעת פייסבוק...\n")
        result = agent.write_facebook_ad(product, offer, audience) if isinstance(agent, CopywritingAgent) \
            else orchestrator.route(f"כתוב מודעת פייסבוק עבור {product}")[1]

    elif choice == "4":
        brand_or_product = input("עסק/מוצר: ").strip()
        tone = input("טון (מקצועי/חברותי/אגרסיבי) [Enter = מקצועי]: ").strip() or "מקצועי"
        if not brand_or_product:
            print("בוטל.")
            return
        print("\nמייצר סלוגנים...\n")
        result = agent.generate_slogans(brand_or_product, tone) if isinstance(agent, CopywritingAgent) \
            else orchestrator.route(f"צור סלוגנים עבור {brand_or_product}")[1]

    elif choice == "5":
        customer_type = input("סוג לקוח (מוסך/פרטי/ציי רכב): ").strip()
        product = input("מוצר/שירות: ").strip()
        objection = input("התנגדות עיקרית (אופציונלי): ").strip()
        if not all([customer_type, product]):
            print("בוטל.")
            return
        print("\nכותב תסריט מכירה...\n")
        result = agent.write_sales_script(customer_type, product, objection) if isinstance(agent, CopywritingAgent) \
            else orchestrator.route(f"כתוב תסריט מכירה ל{customer_type}")[1]

    else:
        print("בחירה לא תקינה.")
        return

    print(f"[סוכן קופירייטינג]:\n{result}\n")


def handle_quote_wizard(orchestrator):
    """אשף הצעת מחיר רגילה"""
    from agents.sales_agent import SalesAgent
    agent = orchestrator.agents.get("סוכן מכירות")

    print("\n--- הצעת מחיר ---")
    print("סוג לקוח: פרטי / מוסך / ציי / קמעונאי")
    customer_type = input("סוג לקוח: ").strip()
    products = input("מוצרים (צמיגים + מידות): ").strip()
    quantity = input("כמות יחידות: ").strip()
    notes = input("הערות נוספות (אופציונלי): ").strip()

    if not all([customer_type, products, quantity]):
        print("בוטל.")
        return

    try:
        qty = int(quantity)
    except ValueError:
        print("כמות חייבת להיות מספר.")
        return

    print("\nמכין הצעת מחיר...\n")
    if isinstance(agent, SalesAgent):
        result = agent.create_quote(customer_type, products, qty, notes)
    else:
        _, result = orchestrator.route(f"צור הצעת מחיר ל{customer_type} עבור {products} כמות {qty}")
    print(f"[סוכן מכירות]:\n{result}\n")


def handle_fleet_quote_wizard(orchestrator):
    """אשף הצעת מחיר לציי רכב"""
    from agents.sales_agent import SalesAgent
    agent = orchestrator.agents.get("סוכן מכירות")

    print("\n--- הצעת מחיר ציי רכב ---")
    company = input("שם החברה: ").strip()
    vehicles = input("מספר רכבים בציי: ").strip()
    tire_type = input("סוג צמיגים (מידה + סוג): ").strip()
    annual_est = input("הערכת צריכה שנתית (יחידות): ").strip()

    if not all([company, vehicles, tire_type, annual_est]):
        print("בוטל.")
        return

    try:
        v = int(vehicles)
        a = int(annual_est)
    except ValueError:
        print("מספרים לא תקינים.")
        return

    print("\nמכין הצעת מחיר לציי רכב...\n")
    if isinstance(agent, SalesAgent):
        result = agent.create_fleet_quote(company, v, tire_type, a)
    else:
        _, result = orchestrator.route(f"הצעת מחיר ציי רכב לחברת {company}")
    print(f"[סוכן מכירות]:\n{result}\n")


def handle_add_lead(orchestrator):
    """אשף הוספת ליד חדש"""
    from agents.sales_agent import SalesAgent
    agent = orchestrator.agents.get("סוכן מכירות")

    print("\n--- הוספת ליד חדש ---")
    name = input("שם איש קשר: ").strip()
    phone = input("טלפון: ").strip()
    print("סוג: פרטי / מוסך / ציי / קמעונאי")
    customer_type = input("סוג לקוח: ").strip()
    interest = input("מה הלקוח מחפש: ").strip()
    notes = input("הערות (אופציונלי): ").strip()

    if not all([name, phone, customer_type, interest]):
        print("בוטל - יש למלא שם, טלפון, סוג ועניין.")
        return

    if isinstance(agent, SalesAgent):
        lead = agent.add_lead(name, phone, customer_type, interest, notes)
        print(f"\nליד נוסף בהצלחה! מזהה: #{lead['id']}")
        print(f"  שם: {lead['name']} | טלפון: {lead['phone']}")
        print(f"  סוג: {lead['customer_type']} | עניין: {lead['interest']}")
        print(f"  סטטוס: {lead['status']}\n")
    else:
        print("סוכן מכירות לא זמין.")


def handle_list_leads(orchestrator):
    """הצגת רשימת לידים"""
    from agents.sales_agent import SalesAgent
    agent = orchestrator.agents.get("סוכן מכירות")

    if not isinstance(agent, SalesAgent):
        print("סוכן מכירות לא זמין.")
        return

    print("\n--- לידים ---")
    print("סנן לפי סטטוס (Enter = הכל): חדש / בטיפול / סגור / אבוד")
    status_filter = input("סטטוס: ").strip()

    leads = agent.list_leads(status_filter)
    if not leads:
        print("אין לידים תואמים.")
        return

    print(f"\n{agent.get_lead_summary()}\n")
    print(f"{'#':<4} {'שם':<20} {'טלפון':<14} {'סוג':<12} {'סטטוס':<10} עניין")
    print("-" * 75)
    for lead in leads:
        print(
            f"{lead['id']:<4} {lead['name']:<20} {lead['phone']:<14} "
            f"{lead['customer_type']:<12} {lead['status']:<10} {lead['interest']}"
        )
    print()


# --- אשפי מלאי ---

def handle_show_inventory(orchestrator):
    """הצגת מלאי מלא עם התראות מלאי נמוך"""
    from agents.inventory_agent import InventoryAgent
    agent = orchestrator.agents.get("סוכן מלאי")

    if not isinstance(agent, InventoryAgent):
        print("סוכן מלאי לא זמין.")
        return

    inventory = agent.list_all()
    print(f"\n--- מלאי ({len(inventory)} פריטים) ---")
    print(agent.print_table())

    low = agent.get_low_stock()
    if low:
        print(f"\n⚠️  התראה: {len(low)} פריט/ים מתחת לכמות מינימום!")
        for item in low:
            print(f"   #{item['id']} {item['brand']} {item['model']} {item['size']} - כמות: {item['quantity']}")
    print()


def handle_add_inventory(orchestrator):
    """אשף הוספת/עדכון פריט במלאי"""
    from agents.inventory_agent import InventoryAgent
    agent = orchestrator.agents.get("סוכן מלאי")

    if not isinstance(agent, InventoryAgent):
        print("סוכן מלאי לא זמין.")
        return

    print("\n--- הוספת/עדכון פריט במלאי ---")
    brand = input("מותג: ").strip()
    model = input("דגם: ").strip()
    size = input("מידה (לדוגמה 205/55R16): ").strip()
    quantity = input("כמות: ").strip()
    cost_price = input("מחיר עלות (₪): ").strip()
    min_qty = input("כמות מינימום להתראה [Enter = 10]: ").strip() or "10"

    if not all([brand, model, size, quantity, cost_price]):
        print("בוטל.")
        return

    try:
        qty = int(quantity)
        cost = float(cost_price)
        min_q = int(min_qty)
    except ValueError:
        print("ערכים מספריים לא תקינים.")
        return

    item = agent.add_or_update(brand, model, size, qty, cost, min_q)
    print(f"\nנשמר! #{item['id']} {item['brand']} {item['model']} {item['size']} | כמות: {item['quantity']} | עלות: {item['cost_price']}₪\n")


def handle_search_inventory(orchestrator):
    """חיפוש צמיג לפי מידה"""
    from agents.inventory_agent import InventoryAgent
    agent = orchestrator.agents.get("סוכן מלאי")

    if not isinstance(agent, InventoryAgent):
        print("סוכן מלאי לא זמין.")
        return

    print("\n--- חיפוש לפי מידה ---")
    size = input("מידה לחיפוש (לדוגמה 205/55R16 או רק 16): ").strip()
    if not size:
        print("בוטל.")
        return

    results = agent.find_by_size(size)
    if not results:
        print(f"לא נמצאו צמיגים עם מידה '{size}'.")
    else:
        print(f"\nנמצאו {len(results)} פריטים:\n")
        print(agent.print_table(results))
    print()


# --- אשפי שירות ---

def handle_book_appointment(orchestrator):
    """אשף קביעת תור"""
    from agents.service_agent import ServiceAgent
    agent = orchestrator.agents.get("סוכן שירות")

    if not isinstance(agent, ServiceAgent):
        print("סוכן שירות לא זמין.")
        return

    print("\n--- קביעת תור ---")
    print(agent.list_own_locations())
    print()

    customer = input("שם לקוח: ").strip()
    phone = input("טלפון: ").strip()
    date = input("תאריך (DD/MM/YYYY): ").strip()
    time = input("שעה (HH:MM): ").strip()
    print("מיקום: צפון / מרכז / חיצוני")
    location = input("מיקום: ").strip()
    service_types = ('החלפת צמיגים', 'עיצוב גלגלים', "תיקון פנצ'ר", 'איזון ולחץ', 'אחסון עונתי')
    print(f"סוגי שירות: {', '.join(service_types)}")
    service_type = input("סוג שירות: ").strip()
    tire_size = input("מידת צמיג (אופציונלי): ").strip()
    notes = input("הערות (אופציונלי): ").strip()

    if not all([customer, phone, date, time, location, service_type]):
        print("בוטל - יש למלא את כל השדות הנדרשים.")
        return

    appt = agent.book_appointment(customer, phone, date, time, location, service_type, tire_size, notes)
    print(f"\nתור נקבע בהצלחה! מזהה: #{appt['id']}")
    print(f"  {appt['customer_name']} | {appt['date']} {appt['time']} | {appt['location']} | {appt['service_type']}\n")


def handle_list_appointments(orchestrator):
    """הצגת תורים"""
    from agents.service_agent import ServiceAgent
    agent = orchestrator.agents.get("סוכן שירות")

    if not isinstance(agent, ServiceAgent):
        print("סוכן שירות לא זמין.")
        return

    print("\n--- תורים ---")
    date_filter = input("סנן לפי תאריך DD/MM/YYYY (Enter = הכל): ").strip()
    location_filter = input("סנן לפי מיקום (Enter = הכל): ").strip()

    appointments = agent.list_appointments(date_filter, location_filter)
    print(f"\n{agent.print_table(appointments)}\n")


def handle_locations(orchestrator):
    """הצגת נקודות שירות"""
    from agents.service_agent import ServiceAgent
    agent = orchestrator.agents.get("סוכן שירות")

    if isinstance(agent, ServiceAgent):
        print(f"\n{agent.list_own_locations()}\n")
    else:
        print("סוכן שירות לא זמין.")


# --- אשפי תמחור ---

def handle_pricing_wizard(orchestrator):
    """אשף חישוב מחיר מכירה"""
    from agents.pricing_agent import PricingAgent
    agent = orchestrator.agents.get("סוכן תמחור")

    if not isinstance(agent, PricingAgent):
        print("סוכן תמחור לא זמין.")
        return

    print("\n--- חישוב מחיר מכירה ---")
    cost = input("עלות יחידה (₪): ").strip()
    print("סוג לקוח: פרטי / מוסך / ציי / קמעונאי")
    customer_type = input("סוג לקוח: ").strip()
    quantity = input("כמות יחידות: ").strip()
    market_price = input("מחיר שוק להשוואה (₪, אופציונלי): ").strip()

    if not all([cost, customer_type, quantity]):
        print("בוטל.")
        return

    try:
        cost_f = float(cost)
        qty = int(quantity)
        market_f = float(market_price) if market_price else None
    except ValueError:
        print("ערכים מספריים לא תקינים.")
        return

    calc = agent.calculate_price(cost_f, customer_type, qty)
    print(f"\n{agent.format_calc_result(calc)}\n")

    analyze = input("לקבל ניתוח AI מפורט? (כן/לא): ").strip().lower()
    if analyze in ("כן", "y", "yes"):
        print("\nמנתח...\n")
        analysis = agent.ai_price_analysis(cost_f, customer_type, qty, market_f)
        print(f"[סוכן תמחור]:\n{analysis}\n")


def handle_flat_tire_wizard(orchestrator):
    """אשף הצעת מחיר פנצ'ר"""
    from agents.pricing_agent import PricingAgent
    agent = orchestrator.agents.get("סוכן תמחור")

    if not isinstance(agent, PricingAgent):
        print("סוכן תמחור לא זמין.")
        return

    print("\n--- הצעת מחיר פנצ'ר ---")
    print("סוגי שירות: תיקון פנצ'ר / בדיקת לחץ / פנצ'ר דחוף")
    service_type = input("סוג שירות: ").strip()
    tire_size = input("מידת הצמיג: ").strip()
    notes = input("הערות (אופציונלי): ").strip()

    if not all([service_type, tire_size]):
        print("בוטל.")
        return

    rate = agent.flat_tire_pricing(service_type)
    print(f"\nטווח מחיר סטנדרטי: {rate[0]}-{rate[1]}₪")
    print("\nמכין הצעת מחיר...\n")
    result = agent.ai_flat_tire_quote(tire_size, service_type, notes)
    print(f"[סוכן תמחור]:\n{result}\n")


# --- אשפי תמיכה ---

def handle_support_wizard(orchestrator):
    """אשף ייעוץ ובחירת צמיג"""
    from agents.support_agent import SupportAgent
    agent = orchestrator.agents.get("סוכן תמיכה")

    if not isinstance(agent, SupportAgent):
        print("סוכן תמיכה לא זמין.")
        return

    print("\n--- ייעוץ בחירת צמיג ---")
    vehicle = input("סוג רכב (לדוגמה: טויוטה קורולה 2020): ").strip()
    budget = input("תקציב (לדוגמה: עד 400₪ ליחידה): ").strip()
    season = input("עונה/תנאים (קיץ/חורף/כל-עונה/הרים): ").strip()
    usage = input("סוג שימוש (עירוני/בין-עירוני/שטח) [Enter = עירוני]: ").strip() or "עירוני"

    if not all([vehicle, budget, season]):
        print("בוטל.")
        return

    print("\nמכין המלצות...\n")
    result = agent.tire_selection_guide(vehicle, budget, season, usage)
    print(f"[סוכן תמיכה]:\n{result}\n")

    # המשך שיחה
    while True:
        follow_up = input("שאלת המשך (Enter לסיום): ").strip()
        if not follow_up:
            break
        print("\n" + agent.chat(follow_up) + "\n")


def handle_faq(orchestrator):
    """אשף שאלות נפוצות"""
    from agents.support_agent import SupportAgent
    agent = orchestrator.agents.get("סוכן תמיכה")

    if not isinstance(agent, SupportAgent):
        print("סוכן תמיכה לא זמין.")
        return

    print(f"\n{agent.list_faq_topics()}\n")
    question = input("שאלה שלך: ").strip()
    if not question:
        print("בוטל.")
        return

    print("\nמחפש תשובה...\n")
    result = agent.answer_faq(question)
    print(f"[סוכן תמיכה]:\n{result}\n")


# --- אשפי דוחות ---

def handle_reports_menu(orchestrator):
    """תפריט דוחות"""
    from agents.reporting_agent import ReportingAgent
    agent = orchestrator.agents.get("סוכן דוחות")

    if not isinstance(agent, ReportingAgent):
        print("סוכן דוחות לא זמין.")
        return

    print("\n--- תפריט דוחות ---")
    print("  1. דוח מלאי")
    print("  2. דוח לידים")
    print("  3. דוח תורים")
    print("  4. שאלה חופשית על הנתונים")

    choice = input("בחירה (1-4): ").strip()

    if choice == "1":
        print("\nמכין דוח מלאי...\n")
        result = agent.inventory_report()
    elif choice == "2":
        print("\nמכין דוח לידים...\n")
        result = agent.leads_report()
    elif choice == "3":
        period = input("תקופה (לדוגמה: היום / השבוע / החודש) [Enter = היום]: ").strip() or "היום"
        print(f"\nמכין דוח תורים ל{period}...\n")
        result = agent.appointments_report(period)
    elif choice == "4":
        question = input("שאלה על הנתונים: ").strip()
        if not question:
            print("בוטל.")
            return
        print("\nמנתח...\n")
        result = agent.run(question)
    else:
        print("בחירה לא תקינה.")
        return

    print(f"[סוכן דוחות]:\n{result}\n")


def handle_daily_summary(orchestrator):
    """סיכום יומי מהיר"""
    from agents.reporting_agent import ReportingAgent
    agent = orchestrator.agents.get("סוכן דוחות")

    if not isinstance(agent, ReportingAgent):
        print("סוכן דוחות לא זמין.")
        return

    print("\nמכין סיכום יומי...\n")
    result = agent.daily_summary()
    print(f"[סוכן דוחות - סיכום יומי]:\n{result}\n")


# --- main ---

def main():
    check_api_key()

    print(BANNER)
    print("טוען סוכנים...")

    from orchestrator.orchestrator import Orchestrator
    orchestrator = Orchestrator()

    agents = orchestrator.list_agents()
    print(f"סוכנים פעילים: {', '.join(agents)}")
    print(MENU)

    while True:
        try:
            user_input = input("אתה> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nשלום!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("/יציאה", "/exit", "יציאה", "exit"):
            print("שלום! להתראות.")
            break

        elif cmd in ("/עזרה", "/help"):
            print(MENU)

        elif cmd in ("/סוכנים", "/agents"):
            print(f"סוכנים פעילים: {', '.join(orchestrator.list_agents())}")

        elif cmd in ("/פרסומת", "/ad"):
            handle_ad_wizard(orchestrator)

        elif cmd in ("/עונה", "/season"):
            handle_season_campaign(orchestrator)

        elif cmd in ("/קופי", "/copy"):
            handle_copy_wizard(orchestrator)

        elif cmd in ("/מכירה", "/quote"):
            handle_quote_wizard(orchestrator)

        elif cmd in ("/ציי", "/fleet"):
            handle_fleet_quote_wizard(orchestrator)

        elif cmd in ("/ליד", "/lead"):
            handle_add_lead(orchestrator)

        elif cmd in ("/לידים", "/leads"):
            handle_list_leads(orchestrator)

        elif cmd in ("/מלאי", "/inventory"):
            handle_show_inventory(orchestrator)

        elif cmd in ("/הוסף", "/additem"):
            handle_add_inventory(orchestrator)

        elif cmd in ("/חפש", "/search"):
            handle_search_inventory(orchestrator)

        elif cmd in ("/תור", "/appt"):
            handle_book_appointment(orchestrator)

        elif cmd in ("/תורים", "/appts"):
            handle_list_appointments(orchestrator)

        elif cmd in ("/סניפים", "/branches"):
            handle_locations(orchestrator)

        elif cmd in ("/מחיר", "/price"):
            handle_pricing_wizard(orchestrator)

        elif cmd in ("/פנצ'ר", "/flat"):
            handle_flat_tire_wizard(orchestrator)

        elif cmd in ("/תמיכה", "/support"):
            handle_support_wizard(orchestrator)

        elif cmd in ("/faq", "/שאלות"):
            handle_faq(orchestrator)

        elif cmd in ("/דוח", "/report"):
            handle_reports_menu(orchestrator)

        elif cmd in ("/סיכום", "/summary"):
            handle_daily_summary(orchestrator)

        elif cmd in ("/נקה", "/clear"):
            for agent in orchestrator.agents.values():
                agent.reset_history()
            print("היסטוריית השיחה נוקתה.")

        else:
            print("\nמעבד בקשה...\n")
            try:
                agent_name, response = orchestrator.route(user_input)
                print(f"[{agent_name}]:\n{response}\n")
            except Exception as e:
                print(f"שגיאה: {e}\n")


if __name__ == "__main__":
    main()
