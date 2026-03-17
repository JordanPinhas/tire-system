"""
PricingAgent - סוכן תמחור לעסק הצמיגים
אחראי על: חישוב מחיר, השוואה לשוק, מחיר פנצ'ר, הנחות כמות
"""

from agents.base_agent import BaseAgent

# Skills
try:
    from skills.exchange_rate import get_exchange_rate, format_rate
    from skills.web_search import search_competitor_prices, format_competitor_report
    _skills_ok = True
except ImportError:
    _skills_ok = False

SYSTEM_PROMPT_FALLBACK = """אתה סוכן תמחור של חברת יבוא צמיגים בישראל.
אתה מחשב מחירי מכירה, מנתח רווחיות ומשווה מחירי שוק. עברית עסקית עם מספרים מדויקים."""

# מרג'ין מינ'-מקס' לפי סוג לקוח (אחוז מעל עלות)
MARGIN_RANGES = {
    "פרטי":      (35, 50),
    "מוסך":      (20, 30),
    "ציי":       (15, 20),
    "קמעונאי":   (10, 15),
}

# הנחות כמות
VOLUME_DISCOUNTS = [
    (50, 0.10),
    (20, 0.06),
    (5,  0.03),
]

# תעריפי פנצ'ר
FLAT_TIRE_RATES = {
    "תיקון פנצ'ר":  (80, 120),
    "בדיקת לחץ":    (0, 50),
    "פנצ'ר דחוף":   (150, 200),
}


class PricingAgent(BaseAgent):
    """סוכן תמחור - חישובים, השוואות שוק ותמחור פנצ'ר"""

    def __init__(self):
        try:
            system_prompt = self.load_prompt("pricing_agent.txt")
        except FileNotFoundError:
            system_prompt = SYSTEM_PROMPT_FALLBACK

        super().__init__(name="סוכן תמחור", system_prompt=system_prompt)

    def run(self, user_input: str) -> str:
        return self.chat(user_input)

    # --- חישובים מקומיים ---

    def calculate_price(self, cost: float, customer_type: str,
                        quantity: int = 1, use_mid_margin: bool = True) -> dict:
        """
        מחשב מחיר מכירה לפי עלות, סוג לקוח וכמות.
        מחזיר dict עם כל פרטי החישוב.
        """
        margin_range = MARGIN_RANGES.get(customer_type, (25, 35))
        margin_pct = (margin_range[0] + margin_range[1]) / 2 if use_mid_margin else margin_range[0]

        base_price = cost * (1 + margin_pct / 100)

        # הנחת כמות
        discount_pct = 0.0
        for min_qty, disc in VOLUME_DISCOUNTS:
            if quantity >= min_qty:
                discount_pct = disc
                break

        final_price = base_price * (1 - discount_pct)
        profit_per_unit = final_price - cost
        total_profit = profit_per_unit * quantity

        return {
            "cost": cost,
            "customer_type": customer_type,
            "quantity": quantity,
            "margin_pct": margin_pct,
            "base_price": round(base_price, 2),
            "volume_discount_pct": discount_pct * 100,
            "final_price": round(final_price, 2),
            "profit_per_unit": round(profit_per_unit, 2),
            "total_profit": round(total_profit, 2),
        }

    def flat_tire_pricing(self, service_type: str) -> tuple[int, int]:
        """מחזיר טווח מחיר לשירות פנצ'ר"""
        return FLAT_TIRE_RATES.get(service_type, (80, 120))

    # --- AI ניתוחים ---

    def ai_price_analysis(self, cost: float, customer_type: str,
                          quantity: int, market_price: float | None = None) -> str:
        """ניתוח תמחור מלא עם AI - כולל המלצה והשוואת שוק"""
        calc = self.calculate_price(cost, customer_type, quantity)

        prompt = (
            f"נתוני תמחור:\n"
            f"- עלות יחידה: {cost}₪\n"
            f"- סוג לקוח: {customer_type}\n"
            f"- כמות: {quantity} יחידות\n"
            f"- מרג'ין מוצע: {calc['margin_pct']}%\n"
            f"- מחיר בסיס: {calc['base_price']}₪\n"
            f"- הנחת כמות: {calc['volume_discount_pct']}%\n"
            f"- מחיר סופי: {calc['final_price']}₪\n"
            f"- רווח ליחידה: {calc['profit_per_unit']}₪\n"
            f"- רווח כולל: {calc['total_profit']}₪\n"
        )
        if market_price:
            diff = calc["final_price"] - market_price
            diff_pct = (diff / market_price) * 100
            prompt += (
                f"\nהשוואת שוק:\n"
                f"- מחיר שוק: {market_price}₪\n"
                f"- ההפרש: {diff:+.1f}₪ ({diff_pct:+.1f}% ממחיר השוק)\n"
            )

        prompt += "\nנתח את התמחור, האם הוא תחרותי? האם יש מה לשנות? מה ההמלצה שלך?"
        return self.chat(prompt, keep_history=False)

    # --- Skills ---

    def get_live_rate(self, currency: str = "EUR") -> str:
        """שולף שער חליפין חי"""
        if not _skills_ok:
            return "skills לא זמינים"
        info = get_exchange_rate(currency)
        return format_rate(info)

    def search_market_prices(self, tire_size: str, brand: str = "") -> str:
        """חיפוש מחירי שוק למידת צמיג"""
        if not _skills_ok:
            return "skills לא זמינים"
        results = search_competitor_prices(tire_size, brand)
        return format_competitor_report(tire_size, brand, results)

    def ai_price_with_market(self, cost: float, customer_type: str,
                              quantity: int, tire_size: str, brand: str = "") -> str:
        """ניתוח תמחור עם השוואת שוק אוטומטית"""
        calc = self.calculate_price(cost, customer_type, quantity)

        market_info = ""
        if _skills_ok:
            results = search_competitor_prices(tire_size, brand)
            prices  = [r["price"] for r in results if r.get("price")]
            if prices:
                avg_market = int(sum(prices) / len(prices))
                market_info = f"\nמחיר שוק ממוצע: {avg_market:,} ₪"

        rate_info = ""
        if _skills_ok:
            rate = get_exchange_rate("EUR")
            if rate.get("rate"):
                rate_info = f"\nשער EUR: {rate['rate']} ₪"

        prompt = (
            f"נתוני תמחור:\n"
            f"- מידה: {tire_size} {brand}\n"
            f"- עלות: {cost} ₪ | סוג לקוח: {customer_type} | כמות: {quantity}\n"
            f"- מרג'ין: {calc['margin_pct']}% → מחיר סופי: {calc['final_price']} ₪\n"
            f"- רווח/יח': {calc['profit_per_unit']} ₪ | רווח כולל: {calc['total_profit']} ₪"
            f"{market_info}{rate_info}\n\n"
            "האם התמחור תחרותי? מה ההמלצה?"
        )
        return self.chat(prompt, keep_history=False)

    def ai_flat_tire_quote(self, tire_size: str, service_type: str, notes: str = "") -> str:
        """הצעת מחיר AI לשירות פנצ'ר"""
        rate_range = self.flat_tire_pricing(service_type)
        prompt = (
            f"לקוח מבקש {service_type}:\n"
            f"מידת צמיג: {tire_size}\n"
            f"טווח מחיר סטנדרטי: {rate_range[0]}-{rate_range[1]}₪\n"
        )
        if notes:
            prompt += f"הערות: {notes}\n"
        prompt += "בנה הצעת מחיר קצרה וברורה ללקוח, עם הסבר קצר."
        return self.chat(prompt, keep_history=False)

    def format_calc_result(self, calc: dict) -> str:
        """פורמט תוצאת חישוב לתצוגה"""
        lines = [
            "--- תוצאת חישוב תמחור ---",
            f"סוג לקוח:      {calc['customer_type']}",
            f"עלות יחידה:    {calc['cost']}₪",
            f"מרג'ין:         {calc['margin_pct']}%",
            f"מחיר בסיס:     {calc['base_price']}₪",
        ]
        if calc["volume_discount_pct"] > 0:
            lines.append(f"הנחת כמות:     {calc['volume_discount_pct']}% (x{calc['quantity']} יח')")
        lines += [
            f"מחיר סופי:     {calc['final_price']}₪",
            f"רווח/יחידה:    {calc['profit_per_unit']}₪",
            f"רווח כולל:     {calc['total_profit']}₪  (x{calc['quantity']} יח')",
        ]
        return "\n".join(lines)
