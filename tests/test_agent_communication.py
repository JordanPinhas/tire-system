"""
בדיקות תקשורת בין סוכנים
הרץ עם: python tests/test_agent_communication.py
"""

from orchestrator.orchestrator import Orchestrator

def test_agents_connected():
    """בדיקה 1: כל הסוכנים מחוברים ל-Orchestrator"""
    print("\n🔍 בדיקה 1: חיבור סוכנים...")
    orch = Orchestrator()
    failed = []
    for name, agent in orch.agents.items():
        if agent._agent_caller is None:
            failed.append(name)
    if failed:
        print(f"  ❌ סוכנים לא מחוברים: {failed}")
    else:
        print(f"  ✅ כל {len(orch.agents)} הסוכנים מחוברים")
    return len(failed) == 0

def test_sales_asks_inventory():
    """בדיקה 2: סוכן מכירות שואל את סוכן המלאי"""
    print("\n🔍 בדיקה 2: Sales → Inventory...")
    orch = Orchestrator()
    sales = orch.agents.get("סוכן מכירות")
    result = sales.ask_agent("סוכן מלאי", "מה הפריטים הזמינים במלאי?")
    if result.startswith("[שגיאה"):
        print(f"  ❌ {result}")
        return False
    print(f"  ✅ קיבל תשובה ({len(result)} תווים)")
    print(f"  📝 תחילת התשובה: {result[:100]}...")
    return True

def test_sales_asks_pricing():
    """בדיקה 3: סוכן מכירות שואל את סוכן התמחור"""
    print("\n🔍 בדיקה 3: Sales → Pricing...")
    orch = Orchestrator()
    sales = orch.agents.get("סוכן מכירות")
    result = sales.ask_agent("סוכן תמחור", "מחיר מומלץ לצמיג 205/55R16")
    if result.startswith("[שגיאה"):
        print(f"  ❌ {result}")
        return False
    print(f"  ✅ קיבל תשובה ({len(result)} תווים)")
    print(f"  📝 תחילת התשובה: {result[:100]}...")
    return True

def test_daily_report():
    """בדיקה 4: דוח יומי מלא"""
    print("\n🔍 בדיקה 4: דוח יומי (Reporting → כל הסוכנים)...")
    orch = Orchestrator()
    reporting = orch.agents.get("סוכן דוחות")
    result = reporting.daily_report()
    has_inventory = "מלאי" in result
    has_leads = "ליד" in result or "מכירות" in result
    has_appointments = "תור" in result or "שירות" in result
    if has_inventory and has_leads and has_appointments:
        print(f"  ✅ דוח מלא התקבל ({len(result)} תווים)")
        print(f"  📝 תחילת הדוח:\n{result[:200]}...")
        return True
    else:
        print(f"  ⚠️ דוח חלקי — בדוק תוכן")
        print(f"  📝 {result[:200]}...")
        return False

def test_full_quote():
    """בדיקה 5: הצעת מחיר מלאה עם מידע מסוכנים"""
    print("\n🔍 בדיקה 5: הצעת מחיר מלאה...")
    orch = Orchestrator()
    sales = orch.agents.get("סוכן מכירות")
    result = sales.create_quote(
        customer_type="מוסך",
        products="205/55R16 Linglong",
        quantity=4
    )
    if len(result) > 100:
        print(f"  ✅ הצעת מחיר נוצרה ({len(result)} תווים)")
        print(f"  📝 תחילת ההצעה:\n{result[:200]}...")
        return True
    print(f"  ❌ הצעה קצרה מדי: {result}")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 בדיקות תקשורת בין סוכנים")
    print("=" * 50)

    results = [
        test_agents_connected(),
        test_sales_asks_inventory(),
        test_sales_asks_pricing(),
        test_daily_report(),
        test_full_quote(),
    ]

    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 50)
    print(f"תוצאות: {passed}/{total} בדיקות עברו")
    if passed == total:
        print("🎉 הכל עובד מצוין!")
    else:
        print("⚠️ יש בדיקות שנכשלו — בדוק את הפלט למעלה")
    print("=" * 50)
