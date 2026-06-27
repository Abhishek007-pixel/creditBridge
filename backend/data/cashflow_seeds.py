"""
Mock AA Cashflow Seeds
Contains 6 months of realistic transactions for demo/simulation personas:
1. Ravi Kumar (9876543210) — Salaried, healthy balances, low risk.
2. Sunita Devi (9123456789) — Street vendor, high volume of cash credits, no salary tag.
3. Default Irregular (9999999999) — Bounced EMI transactions, high variance, low balance.
"""

from datetime import datetime, timedelta

def get_seconds_past(days_ago: int, hour: int = 10) -> str:
    """Return ISO format string of date."""
    dt = datetime.now() - timedelta(days=days_ago)
    dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%d")


# ── RAVI KUMAR: Salaried Pro ────────────────────────────────────────────────
RAVI_TRANSACTIONS = [
    # Salary credits (monthly ₹45,000 on 1st)
    {"date": get_seconds_past(180, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    {"date": get_seconds_past(150, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    {"date": get_seconds_past(120, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    {"date": get_seconds_past(90, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    {"date": get_seconds_past(60, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    {"date": get_seconds_past(30, 9), "amount": 45000, "type": "credit", "description": "SALARY / TCS TECH", "category": "income"},
    
    # Regular Rent payments (₹12,000 on 5th)
    {"date": get_seconds_past(175, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},
    {"date": get_seconds_past(145, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},
    {"date": get_seconds_past(115, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},
    {"date": get_seconds_past(85, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},
    {"date": get_seconds_past(55, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},
    {"date": get_seconds_past(25, 11), "amount": 12000, "type": "debit", "description": "RENT TRANSFER / TO RAJAN PROP", "category": "rent"},

    # Groceries / Retail UPI
    {"date": get_seconds_past(170, 18), "amount": 1200, "type": "debit", "description": "UPI / BIGBASKET / GROCERY", "category": "retail"},
    {"date": get_seconds_past(140, 18), "amount": 1500, "type": "debit", "description": "UPI / DMART / GROCERY", "category": "retail"},
    {"date": get_seconds_past(110, 17), "amount": 800, "type": "debit", "description": "UPI / BIGBASKET / GROCERY", "category": "retail"},
    {"date": get_seconds_past(80, 19), "amount": 2200, "type": "debit", "description": "UPI / SWIGGY INSTAMART", "category": "retail"},
    {"date": get_seconds_past(50, 16), "amount": 950, "type": "debit", "description": "UPI / BIGBASKET / GROCERY", "category": "retail"},
    {"date": get_seconds_past(20, 18), "amount": 1100, "type": "debit", "description": "UPI / ZEPTOMART", "category": "retail"},
    
    # Mutual fund EMI / Investment debits
    {"date": get_seconds_past(165, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
    {"date": get_seconds_past(135, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
    {"date": get_seconds_past(105, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
    {"date": get_seconds_past(75, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
    {"date": get_seconds_past(45, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
    {"date": get_seconds_past(15, 8), "amount": 5000, "type": "debit", "description": "ACH / HDFC MUTUAL FUND SIP", "category": "investment"},
]


# ── SUNITA DEVI: Informal Street Vendor (High-Volume Credits) ────────────────
SUNITA_TRANSACTIONS = [
    # Multi-UPI small credit credits (Simulates customer purchases ₹100 - ₹500 daily)
    {"date": get_seconds_past(178, 12), "amount": 250, "type": "credit", "description": "UPI / PAYTM / CUST-98", "category": "business_sale"},
    {"date": get_seconds_past(177, 14), "amount": 420, "type": "credit", "description": "UPI / PHONEPE / CUST-10", "category": "business_sale"},
    {"date": get_seconds_past(176, 17), "amount": 180, "type": "credit", "description": "UPI / BHIM / CUST-44", "category": "business_sale"},
    {"date": get_seconds_past(175, 13), "amount": 350, "type": "credit", "description": "UPI / PAYTM / CUST-12", "category": "business_sale"},
    {"date": get_seconds_past(148, 12), "amount": 500, "type": "credit", "description": "UPI / PAYTM / CUST-51", "category": "business_sale"},
    {"date": get_seconds_past(147, 15), "amount": 380, "type": "credit", "description": "UPI / PHONEPE / CUST-11", "category": "business_sale"},
    {"date": get_seconds_past(118, 13), "amount": 620, "type": "credit", "description": "UPI / GPAY / CUST-09", "category": "business_sale"},
    {"date": get_seconds_past(117, 16), "amount": 410, "type": "credit", "description": "UPI / PAYTM / CUST-65", "category": "business_sale"},
    {"date": get_seconds_past(88, 11), "amount": 750, "type": "credit", "description": "UPI / PHONEPE / CUST-82", "category": "business_sale"},
    {"date": get_seconds_past(87, 14), "amount": 210, "type": "credit", "description": "UPI / BHIM / CUST-17", "category": "business_sale"},
    {"date": get_seconds_past(58, 12), "amount": 320, "type": "credit", "description": "UPI / GPAY / CUST-39", "category": "business_sale"},
    {"date": get_seconds_past(57, 16), "amount": 850, "type": "credit", "description": "UPI / PAYTM / CUST-71", "category": "business_sale"},
    {"date": get_seconds_past(28, 11), "amount": 440, "type": "credit", "description": "UPI / PHONEPE / CUST-90", "category": "business_sale"},
    {"date": get_seconds_past(27, 15), "amount": 520, "type": "credit", "description": "UPI / GPAY / CUST-31", "category": "business_sale"},

    # Microfinance Loan repayment Success
    {"date": get_seconds_past(160, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},
    {"date": get_seconds_past(130, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},
    {"date": get_seconds_past(100, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},
    {"date": get_seconds_past(70, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},
    {"date": get_seconds_past(40, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},
    {"date": get_seconds_past(10, 10), "amount": 2200, "type": "debit", "description": "UPI / DEBIT / BANDHAN MFI EMI", "category": "emi"},

    # Business material purchase debits
    {"date": get_seconds_past(170, 8), "amount": 8000, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
    {"date": get_seconds_past(140, 8), "amount": 8500, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
    {"date": get_seconds_past(110, 8), "amount": 9000, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
    {"date": get_seconds_past(80, 8), "amount": 7800, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
    {"date": get_seconds_past(50, 8), "amount": 8200, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
    {"date": get_seconds_past(20, 8), "amount": 8800, "type": "debit", "description": "CASH WITHDRAWAL / WHOLESALE VEG", "category": "wholesale"},
]


# ── DEFAULT / IRREGULAR: High-Risk (Low Balance & Bounced Transactions) ───────
IRREGULAR_TRANSACTIONS = [
    # Irregular small credits
    {"date": get_seconds_past(170, 12), "amount": 5000, "type": "credit", "description": "TRANSFER / FROM RAJESH", "category": "gift"},
    {"date": get_seconds_past(120, 11), "amount": 12000, "type": "credit", "description": "UPI / CASH DEPOSIT", "category": "cash_deposit"},
    {"date": get_seconds_past(60, 10), "amount": 8000, "type": "credit", "description": "TRANSFER / FROM RAHUL", "category": "gift"},
    
    # Bounced EMI transactions!
    {"date": get_seconds_past(150, 9), "amount": 12450, "type": "debit", "description": "ACH / EMI DEBIT / CHQ RETURN INSUFFICIENT FUNDS", "category": "penalty"},
    {"date": get_seconds_past(148, 10), "amount": 12450, "type": "debit", "description": "ACH / EMI DEBIT / LN-9849201-B SUCCESS", "category": "emi"},
    
    {"date": get_seconds_past(90, 9), "amount": 12450, "type": "debit", "description": "ACH / EMI DEBIT / CHQ RETURN INSUFFICIENT FUNDS", "category": "penalty"},
    {"date": get_seconds_past(88, 10), "amount": 12450, "type": "debit", "description": "ACH / EMI DEBIT / LN-9849201-B SUCCESS", "category": "emi"},

    {"date": get_seconds_past(30, 9), "amount": 12450, "type": "debit", "description": "ACH / EMI DEBIT / CHQ RETURN INSUFFICIENT FUNDS", "category": "penalty"},

    # High cash withdrawals immediately following deposits (Zero saving balance)
    {"date": get_seconds_past(118, 16), "amount": 11500, "type": "debit", "description": "ATM CASH WITHDRAWAL", "category": "cash_out"},
    {"date": get_seconds_past(58, 14), "amount": 7500, "type": "debit", "description": "ATM CASH WITHDRAWAL", "category": "cash_out"},
]


def get_transactions_by_phone(phone: str) -> list:
    """Return structured seed feed based on phone number."""
    phone = phone.strip()
    if phone == "9876543210":
        return RAVI_TRANSACTIONS
    elif phone == "9123456789":
        return SUNITA_TRANSACTIONS
    else:
        return IRREGULAR_TRANSACTIONS
