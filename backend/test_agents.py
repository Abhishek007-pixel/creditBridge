"""
CreditBridge Agent Verification Script
Runs the Neuro SAN agent pipeline for a demo applicant and prints the output.
"""
import asyncio
import sys
import os
import pprint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_dotenv
from agents.runner import run_agent_pipeline

# Ensure env is loaded
load_dotenv()


async def test():
    print("=" * 60)
    print("      CreditBridge — Running Neuro SAN Agent Network Test")
    print("=" * 60)
    print("Applicant: Ravi Kumar (demo-ravi-001)")
    print("Consented signals: phone_bill, geolocation, merchant")
    print("Running...\n")

    # Run the scoring pipeline
    result = await run_agent_pipeline(
        applicant_id="demo-ravi-001",
        consented_sources=["phone_bill", "geolocation", "merchant", "psychometric"],
        questionnaire_answers=[0, 1, 0, 2, 0, 0, 1, 0, 0, 0],
    )

    print("\n" + "=" * 60)
    print("                      PIPELINE RESULT")
    print("=" * 60)
    print(f"Pipeline Mode: {result.get('pipeline_mode')}")
    print(f"Final Score  : {result.get('final_score')}/850")
    print(f"Risk Category: {result.get('risk_category')}")
    print(f"Decision     : {result.get('decision')}")
    print(f"Loan Rec.    : INR {result.get('loan_recommended'):,}")
    print(f"Interest Rate: {result.get('interest_rate')}%")

    if "fallback_reason" in result:
        print(f"\n⚠️ Fallback Reason: {result.get('fallback_reason')}")

    print("\nBreakdown per signal:")
    breakdown = result.get("breakdown", {})
    for source, details in breakdown.items():
        score = details.get("score")
        reason = details.get("reason")
        consented = "Consented" if details.get("consented") else "Excluded"
        print(f"  - {source:<12} [{consented:<9}] Score: {score:<3} | Reason: {reason}")

    print("\nExplanation Summary:")
    print(result.get("explanation"))
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())
