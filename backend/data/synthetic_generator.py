"""
CreditBridge Synthetic Data Generator
Generates realistic Indian alternative credit data for demo purposes.
All data is DETERMINISTIC based on applicant_id — same applicant
always gets the same data across runs.

Phase 2: Replace with real API connectors (telecom, ecommerce, etc.)
"""
import random
import json
import hashlib
from typing import Any

INDIAN_CITIES = [
    "Guwahati", "Imphal", "Silchar", "Jorhat", "Dibrugarh",
    "Patna", "Muzaffarpur", "Bhagalpur", "Lucknow", "Kanpur",
    "Varanasi", "Agra", "Jaipur", "Jodhpur", "Udaipur",
    "Indore", "Bhopal", "Nagpur", "Pune", "Nashik",
    "Surat", "Vadodara", "Rajkot", "Coimbatore", "Madurai",
    "Visakhapatnam", "Vijayawada", "Warangal", "Bhubaneswar",
    "Rourkela", "Cuttack", "Dehradun", "Haridwar", "Ranchi",
    "Jamshedpur", "Dhanbad", "Mysuru", "Hubli", "Belgaum",
    "Amritsar", "Ludhiana", "Jalandhar", "Shimla", "Chandigarh",
]

PLATFORMS = ["Amazon", "Flipkart", "Meesho", "Myntra", "Nykaa"]
PAYMENT_METHODS = ["Prepaid", "COD", "Mixed"]
AREA_TYPES = ["Urban", "Semi-urban", "Rural"]
ACCOUNT_TYPES = ["Jan Dhan", "Savings", "Current"]
CREDIT_REGULARITY = ["Regular", "Irregular"]
SAVINGS_BEHAVIOR = ["Saves regularly", "Occasional", "No savings"]
CONSISTENCY_RATINGS = ["Excellent", "Good", "Average", "Poor"]


def _seed(applicant_id: str) -> random.Random:
    """Create a seeded random instance so data is deterministic per applicant."""
    seed_val = int(hashlib.md5(applicant_id.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_val)


def generate_applicant_data(applicant_id: str) -> dict:
    """
    Generate all 6 alternative data signals for an applicant.
    Returns deterministic data — same applicant_id always gives same data.
    """
    rng = _seed(applicant_id)

    months = rng.randint(12, 36)
    on_time = rng.randint(int(months * 0.6), months)
    late = rng.randint(0, months - on_time)
    missed = months - on_time - late
    record = (["PAID"] * on_time + ["LATE"] * late + ["MISSED"] * missed)
    rng.shuffle(record)

    phone_bill_data = {
        "months_of_history":     months,
        "on_time_payments":      on_time,
        "late_payments":         late,
        "missed_payments":       missed,
        "disconnections":        rng.randint(0, 2),
        "average_bill_amount":   round(rng.uniform(200, 800), 2),
        "last_12_months_record": record[-12:],
    }

    avg_order = round(rng.uniform(300, 3000), 2)
    ecommerce_data = {
        "platform":          rng.choice(PLATFORMS),
        "months_active":     rng.randint(6, 24),
        "avg_order_value":   avg_order,
        "orders_per_month":  round(rng.uniform(1, 8), 1),
        "return_rate_percent": round(rng.uniform(0, 30), 1),
        "payment_method":    rng.choice(PAYMENT_METHODS),
        "account_age_months": rng.randint(6, 48),
        "total_orders":      rng.randint(10, 200),
    }

    home_stab = rng.randint(6, 36)
    work_stab = rng.randint(3, 24)
    geolocation_data = {
        "home_location_stability_months": home_stab,
        "work_location_stability_months": work_stab,
        "distance_home_to_work_km":       round(rng.uniform(1, 20), 1),
        "city":                           rng.choice(INDIAN_CITIES),
        "area_type":                      rng.choice(AREA_TYPES),
        "frequent_travel":                rng.choice([True, False]),
        "state":                          "Assam" if rng.random() > 0.5 else "India",
    }

    num_merchants = rng.randint(0, 15)
    avg_rating = round(rng.uniform(2.0, 5.0), 1) if num_merchants > 0 else 0.0
    merchant_data = {
        "total_merchants_rated":       num_merchants,
        "average_rating":              avg_rating,
        "years_of_merchant_relationships": rng.randint(0, 5),
        "payment_consistency_rating":  rng.choice(CONSISTENCY_RATINGS),
        "verified_merchants":          rng.randint(0, num_merchants),
    }

    has_account = rng.random() > 0.3
    avg_balance = round(rng.uniform(500, 50000), 2) if has_account else 0.0
    cashflow_data = {
        "has_bank_account":       has_account,
        "account_type":           rng.choice(ACCOUNT_TYPES) if has_account else "None",
        "avg_monthly_balance":    avg_balance,
        "monthly_credits":        rng.randint(1, 4) if has_account else 0,
        "credit_regularity":      rng.choice(CREDIT_REGULARITY) if has_account else "None",
        "bounced_transactions":   rng.randint(0, 5),
        "savings_behavior":       rng.choice(SAVINGS_BEHAVIOR),
        "avg_monthly_debit":      round(avg_balance * rng.uniform(0.3, 0.9), 2),
    }

    return {
        "applicant_id":    applicant_id,
        "phone_bill":      phone_bill_data,
        "ecommerce":       ecommerce_data,
        "geolocation":     geolocation_data,
        "merchant":        merchant_data,
        "cashflow":        cashflow_data,
    }


def score_phone_bill(data: dict) -> tuple[int, str]:
    """Score phone bill data 0-100."""
    d = data
    total = d["months_of_history"]
    if total == 0:
        return 40, "No phone bill history available"

    base = (d["on_time_payments"] / total) * 100
    score = base
    score -= d["disconnections"] * 15
    late_penalty = max(0, d["late_payments"] - 2) * 5
    score -= late_penalty
    if total > 24:
        score += 10

    score = max(0, min(100, round(score)))
    if score >= 80:
        reason = f"{d['on_time_payments']} of {total} months paid on time — excellent discipline"
    elif score >= 60:
        reason = f"{d['on_time_payments']} of {total} months paid on time — good consistency"
    else:
        reason = f"Only {d['on_time_payments']} of {total} months paid on time — irregular payments detected"

    return score, reason


def score_ecommerce(data: dict) -> tuple[int, str]:
    """Score ecommerce behavior 0-100."""
    d = data
    score = 40  # base

    if d["payment_method"] == "Prepaid":
        score += 20
    elif d["payment_method"] == "Mixed":
        score += 10

    if d["return_rate_percent"] < 10:
        score += 15
    elif d["return_rate_percent"] < 20:
        score += 5

    if d["account_age_months"] > 12:
        score += 10

    if 500 <= d["avg_order_value"] <= 2000:
        score += 10
    elif d["avg_order_value"] > 2000:
        score += 5

    if d["orders_per_month"] >= 3:
        score += 10
    elif d["orders_per_month"] >= 1.5:
        score += 5

    score = max(0, min(100, score))
    method = d["payment_method"].lower()
    reason = f"{d['platform']} account, {method} payments, {d['return_rate_percent']}% return rate"
    return score, reason


def score_geolocation(data: dict) -> tuple[int, str]:
    """Score geolocation stability 0-100."""
    d = data
    score = 0

    home_stab = d["home_location_stability_months"]
    if home_stab >= 24:
        score += 40
    elif home_stab >= 12:
        score += 30
    elif home_stab >= 6:
        score += 15

    work_stab = d["work_location_stability_months"]
    if work_stab >= 12:
        score += 30
    elif work_stab >= 6:
        score += 20
    else:
        score += 10

    if d["distance_home_to_work_km"] < 10:
        score += 10

    if d["area_type"] == "Urban":
        score += 10
    elif d["area_type"] == "Semi-urban":
        score += 5

    if not d["frequent_travel"]:
        score += 10

    score = max(0, min(100, score))
    reason = f"Stable in {d['city']} — home {home_stab}mo, work {work_stab}mo"
    return score, reason


def score_merchant(data: dict) -> tuple[int, str]:
    """Score merchant ratings 0-100."""
    d = data
    if d["total_merchants_rated"] == 0:
        return 50, "No merchant data available — using neutral score"

    score = 0
    rating = d["average_rating"]
    if rating >= 4.5:
        score += 50
    elif rating >= 3.5:
        score += 35
    elif rating >= 2.5:
        score += 20
    else:
        score += 5

    merchants = d["total_merchants_rated"]
    if merchants >= 10:
        score += 20
    elif merchants >= 5:
        score += 15
    elif merchants >= 2:
        score += 10

    years = d["years_of_merchant_relationships"]
    if years >= 3:
        score += 20
    elif years >= 1:
        score += 10

    consistency = d["payment_consistency_rating"]
    if consistency == "Excellent":
        score += 10
    elif consistency == "Good":
        score += 5

    score = max(0, min(100, score))
    reason = f"{merchants} merchant relationships, avg rating {rating}/5 — {consistency} payment record"
    return score, reason


def score_cashflow(data: dict) -> tuple[int, str]:
    """Score bank cashflow patterns 0-100."""
    d = data
    if not d["has_bank_account"]:
        return 40, "No bank account — using minimum baseline score"

    score = 20  # has account

    if d["credit_regularity"] == "Regular":
        score += 30

    balance = d["avg_monthly_balance"]
    if balance >= 10000:
        score += 20
    elif balance >= 5000:
        score += 15
    elif balance >= 1000:
        score += 8

    if d["bounced_transactions"] == 0:
        score += 20
    elif d["bounced_transactions"] <= 2:
        score += 10

    savings = d["savings_behavior"]
    if savings == "Saves regularly":
        score += 10
    elif savings == "Occasional":
        score += 5

    score = max(0, min(100, score))
    reason = f"{d['account_type']} account, avg balance ₹{balance:,.0f}, {d['credit_regularity'].lower()} credits"
    return score, reason


def score_psychometric(answers: list) -> tuple[int, str]:
    """
    Score psychometric questionnaire responses 0-100.
    Maps answer indices (0-3) to financial behavior scores.
    Answer 0 = best financial behavior, 3 = worst.
    """
    if not answers:
        return 60, "Psychometric questionnaire not completed — using baseline"

    ANSWER_SCORES = {
        0: [100, 85, 65, 50],   # Q1: repayment timing
        1: [100, 80, 55, 40],   # Q2: unexpected expense handling
        2: [90, 70, 60, 85],    # Q3: loan attitude (opportunity=good, burden=bad)
        3: [100, 80, 60, 30],   # Q4: savings buffer
        4: [100, 80, 50, 20],   # Q5: promise keeping
        5: [100, 75, 60, 20],   # Q6: responsibility attitude
        6: [100, 80, 55, 25],   # Q7: savings months
        7: [100, 80, 50, 15],   # Q8: financial promise keeping
        8: [100, 80, 60, 70],   # Q9: loan purpose
        9: [100, 70, 80, 50],   # Q10: debt attitude
    }

    total = 0
    count = 0
    for i, answer_idx in enumerate(answers):
        if i < len(ANSWER_SCORES) and isinstance(answer_idx, int):
            scores = ANSWER_SCORES[i]
            if 0 <= answer_idx < len(scores):
                total += scores[answer_idx]
                count += 1

    if count == 0:
        return 60, "Could not evaluate questionnaire responses"

    score = round(total / count)
    score = max(0, min(100, score))

    if score >= 80:
        reason = "Strong financial planning mindset and integrity indicators"
    elif score >= 65:
        reason = "Generally positive financial attitudes with some risk factors"
    elif score >= 50:
        reason = "Mixed financial behavior patterns — moderate risk"
    else:
        reason = "Questionnaire indicates financial stress or limited planning"

    return score, reason


def calculate_final_score(agent_scores: dict, weights: dict, consented_sources: list) -> dict:
    """
    Combine all agent scores into a final 300-850 credit score.
    Redistributes weights for non-consented sources.

    Args:
        agent_scores: dict of {source_name: (score, reason)}
        weights: dict of {source_name: weight}
        consented_sources: list of consented source names

    Returns:
        Complete scoring result dict
    """
    active_weights = {k: v for k, v in weights.items() if k in consented_sources}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        total_weight = 1.0
    normalized = {k: v / total_weight for k, v in active_weights.items()}

    weighted_avg = 0.0
    for source, (score, _) in agent_scores.items():
        w = normalized.get(source, 0)
        weighted_avg += score * w

    final_score = round(300 + (weighted_avg / 100) * 550)
    final_score = max(300, min(850, final_score))

    # Determine risk band
    if final_score >= 750:
        risk_cat = "Low Risk"
        loan = 500000
        rate = 10.5
        decision = "Pre-approved"
    elif final_score >= 650:
        risk_cat = "Low-Medium Risk"
        loan = 300000
        rate = 12.0
        decision = "Approved"
    elif final_score >= 550:
        risk_cat = "Medium Risk"
        loan = 100000
        rate = 15.0
        decision = "Conditional Approval"
    elif final_score >= 450:
        risk_cat = "Medium-High Risk"
        loan = 50000
        rate = 18.0
        decision = "Careful Review Required"
    else:
        risk_cat = "High Risk"
        loan = 0
        rate = 0.0
        decision = "Not Recommended"

    # Build score breakdown for display
    breakdown = {}
    for source, (score, reason) in agent_scores.items():
        breakdown[source] = {
            "score": score,
            "reason": reason,
            "weight_used": round(normalized.get(source, 0) * 100, 1),
            "consented": source in consented_sources,
        }

    # Generate plain-language explanation
    sorted_scores = sorted(agent_scores.items(), key=lambda x: x[1][0], reverse=True)
    top2 = sorted_scores[:2]
    bottom2 = sorted_scores[-2:]

    top_signals = " and ".join([s[0].replace("_", " ") for s in top2])
    weak_signals = " and ".join([s[0].replace("_", " ") for s in bottom2 if s[1][0] < 65])

    explanation = (
        f"Your CreditBridge score is {final_score} out of 850. "
        f"This places you in the {risk_cat} category. "
    )
    if loan > 0:
        explanation += (
            f"You are eligible for a loan of up to ₹{loan:,} "
            f"at {rate}% interest per year. "
        )
    explanation += (
        f"\n\nYour strongest signals were your {top_signals}, "
        f"which show consistent and reliable financial behavior. "
    )
    if weak_signals:
        explanation += (
            f"\n\nTo improve your score, focus on strengthening your "
            f"{weak_signals}. Small consistent improvements in these areas "
            f"can significantly boost your score. "
        )
    explanation += (
        "\n\nThis score was generated by an AI system. "
        "A human bank officer will make the final loan decision."
    )

    return {
        "final_score":       final_score,
        "risk_category":     risk_cat,
        "decision":          decision,
        "loan_recommended":  loan,
        "interest_rate":     rate,
        "weighted_average":  round(weighted_avg, 2),
        "breakdown":         breakdown,
        "explanation":       explanation,
        "weights_used":      normalized,
    }
