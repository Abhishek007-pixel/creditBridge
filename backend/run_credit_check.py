"""
CreditBridge — Terminal Agent Runner
Run a full credit scoring pipeline from the command line and save the results.

Usage:
  python run_credit_check.py                          # demo applicant, synthetic mode
  python run_credit_check.py --id demo-priya-002      # specific applicant
  python run_credit_check.py --agents                 # use real Mistral LLM via Neuro SAN
  python run_credit_check.py --all                    # run all 5 demo applicants

Results are saved to: backend/results/<applicant_id>_<timestamp>.json
"""
import asyncio
import json
import os
import sys
import time
import argparse
import io
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows to avoid UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── Demo applicant profiles ──────────────────────────────────────────────
DEMO_APPLICANTS = {
    "demo-priya-002": {
        "name": "Priya Sharma",
        "city": "Lucknow",
        "consented_sources": ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"],
        "questionnaire_answers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "profile": "Street vendor, 2 years phone payments, Flipkart buyer"
    },
    "demo-ravi-001": {
        "name": "Ravi Kumar",
        "city": "Surat",
        "consented_sources": ["phone_bill", "geolocation", "merchant"],
        "questionnaire_answers": [0, 1, 0, 2, 0, 0, 1, 0, 0, 0],
        "profile": "Daily wage worker, stable location, several merchant relationships"
    },
    "demo-ishaq-003": {
        "name": "Mohammed Ishaq",
        "city": "Ranchi",
        "consented_sources": ["phone_bill", "geolocation"],
        "questionnaire_answers": [2, 2, 1, 3, 1, 2, 3, 1, 2, 2],
        "profile": "Seasonal worker, irregular phone payments, minimal data"
    },
    "demo-lakshmi-004": {
        "name": "Lakshmi Devi",
        "city": "Chennai",
        "consented_sources": ["phone_bill", "ecommerce", "cashflow"],
        "questionnaire_answers": [0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        "profile": "Home-based tailor, UPI payments, Meesho seller"
    },
    "demo-arjun-005": {
        "name": "Arjun Patel",
        "city": "Ahmedabad",
        "consented_sources": ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"],
        "questionnaire_answers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "profile": "Small kirana shop owner, full data consent, strong merchant network"
    },
}


def print_separator(char="─", width=60):
    print(char * width)


def print_header(title):
    print_separator("═")
    print(f"  {title}")
    print_separator("═")


def print_result(result: dict, applicant_info: dict, elapsed: float, mode: str):
    """Pretty-print the scoring result to terminal."""
    score = result.get("final_score", 0)
    risk  = result.get("risk_category", "Unknown")
    loan  = result.get("loan_recommended", 0)
    rate  = result.get("interest_rate", 0)
    decision = result.get("decision", "Unknown")

    # Score bar
    bar_len = int((score - 300) / (850 - 300) * 40)
    bar = "█" * bar_len + "░" * (40 - bar_len)

    print(f"\n  Applicant : {applicant_info['name']} ({applicant_info['city']})")
    print(f"  Profile   : {applicant_info['profile']}")
    print(f"  Mode      : {mode}")
    print(f"  Time      : {elapsed:.1f}s")
    print()
    print(f"  CREDIT SCORE : {score} / 850")
    print(f"  [{bar}]")
    print(f"  300          425          550          675          850")
    print()
    print(f"  Risk Band : {risk}")
    print(f"  Decision  : {decision}")
    if loan > 0:
        print(f"  Max Loan  : Rs {loan:,}")
        print(f"  Rate      : {rate}%")
    else:
        print(f"  Max Loan  : Not eligible")
    print()

    # Agent breakdown
    breakdown = result.get("breakdown", {}) or result.get("agent_scores", {})
    if breakdown:
        print("  Signal Breakdown:")
        print_separator()
        for source, data in breakdown.items():
            if isinstance(data, dict):
                s = data.get("score", 0)
                r = data.get("reason", "")
            elif isinstance(data, (list, tuple)) and len(data) >= 2:
                s, r = data[0], data[1]
            else:
                continue
            bar_s = int(s / 100 * 20)
            bar_b = "█" * bar_s + "░" * (20 - bar_s)
            print(f"  {source:<15} {s:>3}/100  [{bar_b}]")
            print(f"                  {str(r)[:55]}")
        print_separator()

    # Explanation
    explanation = result.get("explanation", "")
    if not explanation and result.get("agent_scores"):
        explanation = result.get("agent_scores", {}).get("explanation", "")
    if explanation:
        print("\n  Explanation:")
        # Word wrap at 58 chars
        words = explanation.split()
        line = "  "
        for word in words:
            if len(line) + len(word) + 1 > 60:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
        print()


async def run_single(applicant_id: str, use_agents: bool) -> dict:
    """Run pipeline for one applicant and return result dict."""
    info = DEMO_APPLICANTS.get(applicant_id)
    if not info:
        # Custom applicant — use full consent + neutral answers
        info = {
            "name": applicant_id,
            "city": "Unknown",
            "consented_sources": ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"],
            "questionnaire_answers": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            "profile": "Custom applicant"
        }

    os.environ["USE_AGENTS"] = "true" if use_agents else "false"
    from agents.runner import run_agent_pipeline, run_synthetic_pipeline

    start = time.time()

    if use_agents:
        result = await run_agent_pipeline(
            applicant_id,
            info["consented_sources"],
            info["questionnaire_answers"],
        )
    else:
        result = run_synthetic_pipeline(
            applicant_id,
            info["consented_sources"],
            info["questionnaire_answers"],
        )

    elapsed = time.time() - start
    mode = result.get("pipeline_mode", "synthetic")
    result["applicant_name"] = info["name"]
    result["applicant_city"] = info["city"]
    result["elapsed_seconds"] = round(elapsed, 2)
    result["run_timestamp"] = datetime.now().isoformat()

    return result, info, elapsed, mode


def save_result(result: dict, applicant_id: str) -> str:
    """Save result to JSON file and return path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = RESULTS_DIR / f"{applicant_id}_{ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    return str(filename)


async def main():
    parser = argparse.ArgumentParser(description="CreditBridge Terminal Agent Runner")
    parser.add_argument("--id",     default="demo-priya-002", help="Applicant ID to score")
    parser.add_argument("--agents", action="store_true",      help="Use real Neuro SAN + Mistral LLM")
    parser.add_argument("--all",    action="store_true",      help="Run all 5 demo applicants")
    args = parser.parse_args()

    mode_label = "NEURO SAN + Mistral LLM" if args.agents else "SYNTHETIC (deterministic, no API)"

    print_header(f"CreditBridge Terminal Runner  |  {mode_label}")
    print()

    applicant_ids = list(DEMO_APPLICANTS.keys()) if args.all else [args.id]
    all_results = []

    for aid in applicant_ids:
        print(f"  Scoring: {aid} ...")
        try:
            result, info, elapsed, mode = await run_single(aid, args.agents)
            print_result(result, info, elapsed, mode)
            saved_path = save_result(result, aid)
            print(f"  Saved   -> {saved_path}")
            print()
            all_results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Summary table if multiple applicants
    if len(all_results) > 1:
        print_header("Summary — All Applicants")
        print(f"  {'Name':<20} {'Score':>6}  {'Risk':<25} {'Loan':>12}  Mode")
        print_separator()
        for r in all_results:
            name  = r.get("applicant_name", "?")[:20]
            score = r.get("final_score", 0)
            risk  = r.get("risk_category", "?")[:25]
            loan  = r.get("loan_recommended", 0)
            mode  = r.get("pipeline_mode", "?")[:12]
            loan_str = f"Rs {loan:,}" if loan > 0 else "Not eligible"
            print(f"  {name:<20} {score:>6}  {risk:<25} {loan_str:>12}  {mode}")
        print_separator()

        # Save combined results
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_path = RESULTS_DIR / f"all_applicants_{ts}.json"
        with open(combined_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  Combined results -> {combined_path}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
