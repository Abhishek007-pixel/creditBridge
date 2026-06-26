export interface PsychometricQuestion {
  id: number;
  question: string;
  category: string;
  description: string;
  options: {
    text: string;
    description: string;
  }[];
}

export const psychometricQuestions: PsychometricQuestion[] = [
  {
    id: 1,
    question: "When you receive a monthly bill (like electricity or phone), when do you usually pay it?",
    category: "Repayment Timing & Discipline",
    description: "Evaluates proactive repayment behavior and financial prioritization.",
    options: [
      { text: "Immediately, as soon as it is generated", description: "Demonstrates highly proactive credit and bill-paying behavior." },
      { text: "A few days before the due date", description: "Indicates safe and organized cashflow management." },
      { text: "On the exact due date", description: "Acceptable latency, but indicates potential tight budgeting." },
      { text: "A few days after the due date, with a grace period", description: "Indicates possible cashflow bottlenecks or lack of focus on timing." }
    ]
  },
  {
    id: 2,
    question: "If your business or household encounters an unexpected expense of ₹10,000, how would you manage it?",
    category: "Shock Response & Resilience",
    description: "Evaluates financial cushion, risk management, and credit dependency.",
    options: [
      { text: "Pay fully out of existing personal savings", description: "Indicates strong safety reserves and zero immediate reliance on debt." },
      { text: "Cover parts with savings and trim non-essential expenses", description: "Demonstrates active adjustment and responsible budgeting." },
      { text: "Borrow from family, friends, or coworkers", description: "Signals weak capital reserve, but reliance on trusted communities." },
      { text: "Take an immediate high-interest loan from local informal lenders", description: "Signals high financial risk, distress, and exposure to predatory debt." }
    ]
  },
  {
    id: 3,
    question: "What is your general view on taking a bank loan for your livelihood/micro-business?",
    category: "Credit Attitude & Mindset",
    description: "Assesses risk aversion, alignment with capital growth, and debt-burden perspective.",
    options: [
      { text: "It is an investment strategy to expand and increase profits", description: "Understands productive leverage and ROI growth." },
      { text: "It is a helpful tool when self-funding is temporarily restricted", description: "Treats credit as a calculated secondary option." },
      { text: "It is a heavy stressful burden, only to be used in emergencies", description: "Highly risk-averse, which is safe, but may limit commercial growth." },
      { text: "It is a quick source of cash to solve immediate lifestyle challenges", description: "Signals danger of using capital loans for non-productive expenses." }
    ]
  },
  {
    id: 4,
    question: "How much of your monthly income are you able to save consistently?",
    category: "Savings Buffer & Habit",
    description: "Metrics of direct household income surplus and wealth preservation.",
    options: [
      { text: "More than 20% of my earnings", description: "Excellent financial health; outstanding wealth retention." },
      { text: "Between 10% to 20% of my earnings", description: "Solid financial planning with steady capital accumulation." },
      { text: "Less than 10% of my earnings", description: "Tight surplus; vulnerable to slight economic shifts." },
      { text: "I live day-to-day and save nothing", description: "High credit invisible vulnerability; zero margin of safety." }
    ]
  },
  {
    id: 5,
    question: "How do you rate your commitment to promises made in your work/business?",
    category: "Social Trust & Dependability",
    description: "Surrogates integrity, reputational collateral, and community standing.",
    options: [
      { text: "I fulfill every promise on time regardless of personal cost", description: "Outstanding internal locus of responsibility." },
      { text: "I consistently deliver on my words, communicating lapses proactively", description: "Strong professional integrity and accountability." },
      { text: "I attempt to deliver but sometimes external factors cause delays", description: "Moderate dependability; high variance in output." },
      { text: "Promises depend on circumstances; flexibility is more vital", description: "Low prioritization of commitment, indicating higher default risk." }
    ]
  },
  {
    id: 6,
    question: "If a supplier accidentally overpays you or delivers extra raw materials, what do you do?",
    category: "Integrity & Moral Invariant",
    description: "Measures underlying moral hazard and credit repayment willingness.",
    options: [
      { text: "Proactively report it immediately and return the excess", description: "High moral standing; absolute credit reliability." },
      { text: "Wait for them to realize the mistake, then return it willingly", description: "Fairly honest, but passive and reactive to moral duties." },
      { text: "Keep it unless they explicitly ask for it", description: "Prone to moral hazard; opportunistic behavior." },
      { text: "Deny receiving it and store it as a lucky bonus", description: "High operational risk; highly susceptible to strategic default." }
    ]
  },
  {
    id: 7,
    question: "How long could you sustain your regular expenses if your primary income source stopped tomorrow?",
    category: "Liquidity Reserve Length",
    description: "Evaluates cash runway length of-sight and solvency stability.",
    options: [
      { text: "More than 6 months", description: "Extremely resilient; superb runway for absolute peace of mind." },
      { text: "Between 3 to 6 months", description: "Safe margin; sufficient to adapt or restructure." },
      { text: "Between 1 to 2 months", description: "Vulnerable; must find immediate alternate income to survive." },
      { text: "Less than a month", description: "Critical emergency zone; highly prone to instant insolvency." }
    ]
  },
  {
    id: 8,
    question: "What is your history with informal agreements (like village chits or local store tabs)?",
    category: "Historical Social Credit",
    description: "Micro-bureau surrogate of local peer-to-peer credit responsibility.",
    options: [
      { text: "Paid back fully on time, always keeping relationships flawless", description: "Perfect repayment record in community networks." },
      { text: "Slight delays occasionally, but settled with complete transparency", description: "Good communication; reliable in the long run." },
      { text: "Often delayed due to cash matching but eventually cleared", description: "Operational delays; cash flow is irregular." },
      { text: "Had disputes or settled with some write-offs/forgiveness", description: "Signals history of defaults or credit friction." }
    ]
  },
  {
    id: 9,
    question: "What is the primary target area you want to fund with this business loan?",
    category: "CapEx Utility / Allocation",
    description: "Evaluates loan use strategy and revenue-generating potential.",
    options: [
      { text: "Capital assets or machinery that directly multiply output", description: "Highly generative allocation of funds with positive cash loops." },
      { text: "Acquiring extra raw material inventory/supplies at wholesale discounts", description: "Direct liquidity conversion to inventory turnover booster." },
      { text: "Day-to-day general working capital (accruals, overheads)", description: "Short-term maintenance allocation; non-generative buffer." },
      { text: "Paying old credit balances or personal domestic needs", description: "Refinancing or consumption; non-commercial redirection risk." }
    ]
  },
  {
    id: 10,
    question: "What is your core rule regarding taking secondary debts or credits?",
    category: "Leverage & Debt Appetite",
    description: "Over-leverage threat assessment and control discipline.",
    options: [
      { text: "Never take more than one credit at any given time", description: "Superb self-regulation and strict guard against credit stacking." },
      { text: "Only borrow if the combined payments are less than 30% of profits", description: "Understands debt-to-income and cash coverage safety ceilings." },
      { text: "Borrow whenever credit is available, managing them manually", description: "Aggressive leverage appetite; vulnerable to cascade failures." },
      { text: "Borrow from active sources to repay previous older dues", description: "Classic ponzi-finance pattern; extremely high warning flag." }
    ]
  }
];
