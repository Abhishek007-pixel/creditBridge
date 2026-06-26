// Alternate Credit Scoring Algorithms and Data Generators for CreditBridge

export interface PhoneBillData {
  months_of_history: number;
  on_time_payments: number;
  late_payments: number;
  missed_payments: number;
  disconnections: number;
  average_bill_amount: number;
}

export interface EcommerceData {
  platform: string;
  months_active: number;
  avg_order_value: number;
  orders_per_month: number;
  return_rate_percent: number;
  payment_method: string;
}

export interface GeolocationData {
  home_location_stability_months: number;
  work_location_stability_months: number;
  distance_home_to_work_km: number;
  area_type: string;
  frequent_travel: boolean;
  city: string;
}

export interface MerchantData {
  total_merchants_rated: number;
  average_rating: number;
  years_of_merchant_relationships: number;
  payment_consistency_rating: string;
}

export interface CashflowData {
  has_bank_account: boolean;
  account_type: string;
  avg_monthly_balance: number;
  monthly_credits: number;
  credit_regularity: string;
  bounced_transactions: number;
  savings_behavior: string;
}

export interface ApplicantAlternativeData {
  phone_bill: PhoneBillData;
  ecommerce: EcommerceData;
  geolocation: GeolocationData;
  merchant: MerchantData;
  cashflow: CashflowData;
}

// Deterministic deterministic random generator
export function seededRandom(seedStr: string) {
  let hash = 0;
  for (let i = 0; i < seedStr.length; i++) {
    hash = seedStr.charCodeAt(i) + ((hash << 5) - hash);
  }
  return () => {
    const x = Math.sin(hash++) * 10000;
    return x - Math.floor(x);
  };
}

export function generateAlternativeData(seedKey: string): ApplicantAlternativeData {
  const rng = seededRandom(seedKey);

  const cities = ["Guwahati", "Imphal", "Silchar", "Jorhat", "Dibrugarh", "Lucknow", "Varanasi", "Surat", "Coimbatore", "Ranchi"];
  const platforms = ["Amazon", "Flipkart", "Meesho", "Myntra", "Nykaa"];
  const paymentMethods = ["Prepaid", "COD", "Mixed"];
  const areaTypes = ["Urban", "Semi-urban", "Rural"];
  const accountTypes = ["Jan Dhan", "Savings", "Current"];
  const creditRegularities = ["Regular", "Irregular"];
  const savingsBehaviors = ["Saves regularly", "Occasional", "No savings"];
  const consistencyRatings = ["Excellent", "Good", "Average", "Poor"];

  const phoneMonths = Math.floor(rng() * 25) + 12; // 12 to 36
  const phoneOnTime = Math.floor(rng() * (phoneMonths - Math.floor(phoneMonths * 0.6) + 1)) + Math.floor(phoneMonths * 0.6);
  const phoneLate = Math.floor(rng() * (phoneMonths - phoneOnTime));
  const phoneMissed = phoneMonths - phoneOnTime - phoneLate;

  return {
    phone_bill: {
      months_of_history: phoneMonths,
      on_time_payments: phoneOnTime,
      late_payments: phoneLate,
      missed_payments: phoneMissed,
      disconnections: Math.floor(rng() * 3), // 0 to 2
      average_bill_amount: Math.round((rng() * 1000 + 200) * 100) / 100
    },
    ecommerce: {
      platform: platforms[Math.floor(rng() * platforms.length)],
      months_active: Math.floor(rng() * 43) + 6, // 6 to 48
      avg_order_value: Math.round((rng() * 3700 + 300) * 100) / 100,
      orders_per_month: Math.round((rng() * 7 + 1) * 10) / 10,
      return_rate_percent: Math.round(rng() * 30 * 10) / 10,
      payment_method: paymentMethods[Math.floor(rng() * paymentMethods.length)]
    },
    geolocation: {
      home_location_stability_months: Math.floor(rng() * 31) + 6, // 6 to 36
      work_location_stability_months: Math.floor(rng() * 22) + 3, // 3 to 24
      distance_home_to_work_km: Math.round((rng() * 19 + 1) * 10) / 10,
      city: cities[Math.floor(rng() * cities.length)],
      area_type: areaTypes[Math.floor(rng() * areaTypes.length)],
      frequent_travel: rng() > 0.6
    },
    merchant: {
      total_merchants_rated: Math.floor(rng() * 16), // 0 to 15
      average_rating: Math.round((rng() * 3.0 + 2.0) * 10) / 10,
      years_of_merchant_relationships: Math.floor(rng() * 6), // 0 to 5
      payment_consistency_rating: consistencyRatings[Math.floor(rng() * consistencyRatings.length)]
    },
    cashflow: {
      has_bank_account: rng() > 0.15, // 85% chance banked
      account_type: accountTypes[Math.floor(rng() * accountTypes.length)],
      avg_monthly_balance: Math.round(rng() * 49500 + 500),
      monthly_credits: Math.floor(rng() * 4) + 1,
      credit_regularity: creditRegularities[Math.floor(rng() * creditRegularities.length)],
      bounced_transactions: Math.floor(rng() * 6), // 0 to 5
      savings_behavior: savingsBehaviors[Math.floor(rng() * savingsBehaviors.length)]
    }
  };
}

export function scorePhoneBill(data: PhoneBillData): { score: number; reason: string } {
  const total = data.months_of_history;
  if (!total) return { score: 40, reason: "No telecommunication bill logs synced" };

  const base = (data.on_time_payments / total) * 100;
  let score = base;
  score -= data.disconnections * 15;
  const latePenalty = Math.max(0, data.late_payments - 2) * 5;
  score -= latePenalty;
  
  if (total > 24) score += 10;

  score = Math.max(0, Math.min(100, Math.round(score)));

  let reason = "";
  if (score >= 80) {
    reason = `Excellent telemetry discipline: paid on time in ${data.on_time_payments}/${total} monthly billing cycles.`;
  } else if (score >= 60) {
    reason = `Moderate bill payment loyalty: ${data.on_time_payments}/${total} cycles met prompt payment criteria.`;
  } else {
    reason = `High bill payment variance: ${data.on_time_payments}/${total} on-time with ${data.disconnections} operational disconnections.`;
  }

  return { score, reason };
}

export function scoreEcommerce(data: EcommerceData): { score: number; reason: string } {
  let score = 40;

  if (data.payment_method === "Prepaid") {
    score += 20;
  } else if (data.payment_method === "Mixed") {
    score += 10;
  }

  if (data.return_rate_percent < 10) {
    score += 15;
  } else if (data.return_rate_percent < 20) {
    score += 5;
  }

  if (data.months_active > 12) {
    score += 10;
  }

  if (data.avg_order_value >= 500 && data.avg_order_value <= 2000) {
    score += 10;
  } else if (data.avg_order_value > 2000) {
    score += 5;
  }

  if (data.orders_per_month >= 3) {
    score += 10;
  } else if (data.orders_per_month >= 1.5) {
    score += 5;
  }

  score = Math.max(0, Math.min(100, score));

  const reason = `E-commerce buyer profile on ${data.platform} over ${data.months_active} months, displaying ${data.payment_method.toLowerCase()} payment choices and a ${data.return_rate_percent}% return rate.`;
  return { score, reason };
}

export function scoreGeolocation(data: GeolocationData): { score: number; reason: string } {
  let score = 0;

  if (data.home_location_stability_months >= 24) {
    score += 40;
  } else if (data.home_location_stability_months >= 12) {
    score += 30;
  } else if (data.home_location_stability_months >= 6) {
    score += 15;
  }

  if (data.work_location_stability_months >= 12) {
    score += 30;
  } else if (data.work_location_stability_months >= 6) {
    score += 20;
  } else {
    score += 10;
  }

  if (data.distance_home_to_work_km < 10) {
    score += 10;
  }

  if (data.area_type === "Urban") {
    score += 10;
  } else if (data.area_type === "Semi-urban") {
    score += 5;
  }

  if (!data.frequent_travel) {
    score += 10;
  }

  score = Math.max(0, Math.min(100, score));

  const reason = `Rooted community stability index in ${data.city}. Local residence of ${data.home_location_stability_months} months with steady commute distance of ${data.distance_home_to_work_km} km.`;
  return { score, reason };
}

export function scoreMerchant(data: MerchantData): { score: number; reason: string } {
  if (data.total_merchants_rated === 0) {
    return { score: 50, reason: "No professional B2B or small merchant trade credentials registered." };
  }

  let score = 0;

  if (data.average_rating >= 4.5) {
    score += 50;
  } else if (data.average_rating >= 3.5) {
    score += 35;
  } else if (data.average_rating >= 2.5) {
    score += 20;
  } else {
    score += 5;
  }

  if (data.total_merchants_rated >= 10) {
    score += 20;
  } else if (data.total_merchants_rated >= 5) {
    score += 15;
  } else if (data.total_merchants_rated >= 2) {
    score += 10;
  }

  if (data.years_of_merchant_relationships >= 3) {
    score += 20;
  } else if (data.years_of_merchant_relationships >= 1) {
    score += 10;
  }

  if (data.payment_consistency_rating === "Excellent") {
    score += 10;
  } else if (data.payment_consistency_rating === "Good") {
    score += 5;
  }

  score = Math.max(0, Math.min(100, score));

  const reason = `Credibility and trust index verified by ${data.total_merchants_rated} active local suppliers, with an average rating of ${data.average_rating}/5.`;
  return { score, reason };
}

export function scoreCashflow(data: CashflowData): { score: number; reason: string } {
  if (!data.has_bank_account) {
    return { score: 40, reason: "Currently unbanked. Micro-savings loops and cash transactions have zero digital trails." };
  }

  let score = 20;

  if (data.credit_regularity === "Regular") {
    score += 30;
  }

  if (data.avg_monthly_balance >= 10000) {
    score += 20;
  } else if (data.avg_monthly_balance >= 5000) {
    score += 15;
  } else if (data.avg_monthly_balance >= 1000) {
    score += 8;
  }

  if (data.bounced_transactions === 0) {
    score += 20;
  } else if (data.bounced_transactions <= 2) {
    score += 10;
  }

  if (data.savings_behavior === "Saves regularly") {
    score += 10;
  } else if (data.savings_behavior === "Occasional") {
    score += 5;
  }

  score = Math.max(0, Math.min(100, score));

  const reason = `Active ${data.account_type} account demonstrating ${data.credit_regularity.toLowerCase()} monthly inflow cycles, having average balance of ₹${data.avg_monthly_balance} with ${data.bounced_transactions} bounced transactions.`;
  return { score, reason };
}

export function scorePsychometric(answers: number[]): { score: number; reason: string } {
  if (!answers || answers.length === 0) {
    return { score: 60, reason: "Psychometric planning evaluation incomplete. Standard neutral baseline applied." };
  }

  const ANSWER_SCORES: { [key: number]: number[] } = {
    0: [100, 85, 65, 50],
    1: [100, 80, 55, 40],
    2: [90, 70, 60, 85],
    3: [100, 80, 60, 30],
    4: [100, 80, 50, 20],
    5: [100, 75, 60, 20],
    6: [100, 80, 55, 25],
    7: [100, 80, 50, 15],
    8: [100, 80, 60, 70],
    9: [100, 70, 80, 50]
  };

  let totalPoints = 0;
  let count = 0;

  answers.forEach((choice, index) => {
    const scoreMap = ANSWER_SCORES[index];
    if (scoreMap && typeof choice === 'number' && choice >= 0 && choice <= 3) {
      totalPoints += scoreMap[choice];
      count++;
    }
  });

  if (count === 0) return { score: 60, reason: "Error parsing choices" };

  const score = Math.round(totalPoints / count);

  let reason = "";
  if (score >= 80) {
    reason = "Superb forward financial-intent, low moral hazard, and outstanding long-term prioritization rules.";
  } else if (score >= 65) {
    reason = "Safe decision-making attitudes with moderate buffer reserves and low defaults risk.";
  } else {
    reason = "Liquidity vulnerability noticed: behavioral traits suggest heavy sensitivity to urgent expenses.";
  }

  return { score, reason };
}

export interface ScoreReport {
  final_score: number;
  risk_category: string;
  decision: string;
  loan_recommended: number;
  interest_rate: number;
  weighted_average: number;
  breakdown: {
    [key: string]: {
      score: number;
      reason: string;
      weight_used: number;
      consented: boolean;
      description: string;
    };
  };
  weights_used: { [key: string]: number };
  explanation: string;
}

export function evaluateCreditScore(
  applicantId: string,
  consentedSources: string[],
  answers: number[],
  customWeights?: { [key: string]: number }
): ScoreReport {
  const data = generateAlternativeData(applicantId);

  // Default weights
  const defaultWeights: { [key: string]: number } = customWeights || {
    phone_bill: 0.25,
    cashflow: 0.20,
    psychometric: 0.20,
    geolocation: 0.15,
    ecommerce: 0.12,
    merchant: 0.08
  };

  const signalMetadata: { [key: string]: string } = {
    phone_bill: "Utility EMI & prompt pay discipline",
    cashflow: "Surplus cash accumulation metric",
    psychometric: "Mindset risk, moral boundaries and budget intent",
    geolocation: "Rooted physical residential stability index",
    ecommerce: "Digital disposable liquidity footprint",
    merchant: "Reputational supplier verification matrix"
  };

  const scores: { [key: string]: { score: number; reason: string } } = {
    phone_bill: scorePhoneBill(data.phone_bill),
    ecommerce: scoreEcommerce(data.ecommerce),
    geolocation: scoreGeolocation(data.geolocation),
    merchant: scoreMerchant(data.merchant),
    cashflow: scoreCashflow(data.cashflow),
    psychometric: scorePsychometric(answers)
  };

  // DPDP Compliance: Dynamic Weight Redistribution
  const activeSources = consentedSources.filter(s => s in defaultWeights);
  if (!activeSources.includes("psychometric")) {
    activeSources.push("psychometric"); // Psychometric is always present as a core behavioral validator
  }

  let totalActiveDefaultWeight = 0;
  active_sources: for (const src of activeSources) {
    totalActiveDefaultWeight += defaultWeights[src] || 0;
  }
  if (totalActiveDefaultWeight === 0) totalActiveDefaultWeight = 1;

  const normalizedWeights: { [key: string]: number } = {};
  for (const src of activeSources) {
    normalizedWeights[src] = (defaultWeights[src] || 0) / totalActiveDefaultWeight;
  }

  // Calculate Weighted Average
  let weightedAvg = 0;
  const breakdown: any = {};

  for (const key in scores) {
    const isConsented = consentedSources.includes(key) || key === "psychometric";
    const weightUsed = isConsented ? (normalizedWeights[key] || 0) : 0;
    
    if (isConsented) {
      weightedAvg += scores[key].score * weightUsed;
    }

    breakdown[key] = {
      score: scores[key].score,
      reason: scores[key].reason,
      weight_used: Math.round(weightUsed * 100 * 10) / 10,
      consented: isConsented,
      description: signalMetadata[key]
    };
  }

  // Map to Credit Score (300 to 850)
  const finalScore = Math.max(300, Math.min(850, Math.round(300 + (weightedAvg / 100) * 550)));

  // Determine loan details and category
  let riskCategory = "High Risk";
  let decision = "Not Recommended";
  let loanRecommended = 0;
  let interestRate = 0;

  if (finalScore >= 750) {
    riskCategory = "Low Risk";
    decision = "Pre-approved";
    loanRecommended = 500000;
    interestRate = 10.5;
  } else if (finalScore >= 650) {
    riskCategory = "Low-Medium Risk";
    decision = "Approved";
    loanRecommended = 300000;
    interestRate = 12.0;
  } else if (finalScore >= 550) {
    riskCategory = "Medium Risk";
    decision = "Conditional Approval";
    loanRecommended = 100000;
    interestRate = 15.0;
  } else if (finalScore >= 450) {
    riskCategory = "Medium-High Risk";
    decision = "Careful Review Required";
    loanRecommended = 50000;
    interestRate = 18.0;
  } else {
    riskCategory = "High Risk";
    decision = "Not Recommended";
    loanRecommended = 0;
    interestRate = 0.0;
  }

  // Explanation paragraph
  const sortedSignals = Object.keys(scores)
    .filter(k => consentedSources.includes(k) || k === "psychometric")
    .sort((a, b) => scores[b].score - scores[a].score);

  const topStrength = sortedSignals[0] ? sortedSignals[0].replace("_", " ") : "";
  const secondStrength = sortedSignals[1] ? sortedSignals[1].replace("_", " ") : "";
  const weakestSignal = sortedSignals[sortedSignals.length - 1] ? sortedSignals[sortedSignals.length - 1].replace("_", " ") : "";

  let explanation = `Your CreditBridge alternate credit score is computed as ${finalScore} out of 850, placing you in the ${riskCategory} band. `;
  if (loanRecommended > 0) {
    explanation += `Lenders recommend an eligible micro-credit line of ₹${loanRecommended.toLocaleString("en-IN")} at an annualized interest rate of ${interestRate}%. `;
  } else {
    explanation += `Currently, your alternate digital surrogates do not meet the minimum safety metrics for automatic lending pathways. `;
  }
  
  if (topStrength) {
    explanation += `Your primary behavioral engine of strength is your ${topStrength}${secondStrength ? ` followed by your ${secondStrength}` : ""}, which reflect positive financial discipline. `;
  }
  
  if (weakestSignal && scores[sortedSignals[sortedSignals.length - 1]].score < 65) {
    explanation += `To significantly optimize your rating for future credit expansions, we recommend strengthening your ${weakestSignal} through persistent consistency. `;
  }

  explanation += "\n\nThis decision is modeled securely on consent-based GDPR/DPDP-compliant data vectors representing human character. A bank officer of UCO Bank will verify the validation trail for absolute execution.";

  return {
    final_score: finalScore,
    risk_category: riskCategory,
    decision,
    loan_recommended: loanRecommended,
    interest_rate: interestRate,
    weighted_average: Math.round(weightedAvg * 10) / 10,
    breakdown,
    weights_used: normalizedWeights,
    explanation
  };
}
