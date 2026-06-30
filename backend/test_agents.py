"""
CreditBridge Agent Test Script
Run this BEFORE the demo to verify the full pipeline works.

Usage:
  python test_agents.py                     — test synthetic pipeline + coded tools
  python test_agents.py --agents            — test real Neuro SAN pipeline
  python test_agents.py --agents --verbose  — test with full breakdown

Expected output (synthetic): Score in range 300-850, all signals scored.
Expected output (agents):    Same but pipeline_mode = "neuro_san"
"""
import asyncio
import json
import sys
import os
import io

# Ensure UTF-8 output on Windows to avoid UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()



TEST_CASES = [
    {
        "name": "Priya Sharma (High scorer — all data)",
        "applicant_id": "demo-priya-002",
        "consented_sources": ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"],
        "questionnaire_answers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "expected_range": (580, 850),
    },
    {
        "name": "Ravi Kumar (Mid scorer — partial data)",
        "applicant_id": "demo-ravi-001",
        "consented_sources": ["phone_bill", "geolocation", "merchant"],
        "questionnaire_answers": [0, 1, 0, 2, 0, 0, 1, 0, 0, 0],
        "expected_range": (550, 750),
    },
    {
        "name": "Mohammed Ishaq (Low scorer — minimal data)",
        "applicant_id": "demo-ishaq-003",
        "consented_sources": ["phone_bill", "geolocation"],
        "questionnaire_answers": [2, 2, 1, 3, 1, 2, 3, 1, 2, 2],
        "expected_range": (350, 600),
    },
]


async def test_coded_tools():
    """Test that coded tools can be imported and invoked correctly."""
    print("\n" + "=" * 60)
    print("Test 1 — Coded Tool Imports & Invocations")
    print("=" * 60)

    all_ok = True
    tools = [
        ("coded_tools.creditbridge.bill_consistency_tool", "BillConsistencyScoringTool"),
        ("coded_tools.creditbridge.ecommerce_tool", "EcommerceScoringTool"),
        ("coded_tools.creditbridge.geolocation_tool", "GeolocationScoringTool"),
        ("coded_tools.creditbridge.merchant_tool", "MerchantScoringTool"),
        ("coded_tools.creditbridge.cashflow_tool", "CashflowScoringTool"),
        ("coded_tools.creditbridge.financial_commitment_tool", "FinancialCommitmentScoringTool"),
    ]

    for module_path, class_name in tools:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            tool = cls()
            result = await tool.async_invoke({"applicant_id": "demo-priya-002"}, {})
            score = result.get("score", result.get("preliminary_score", result.get("final_cashflow_score", result.get("final_bill_score", "?"))))
            status = result.get("status", "unknown")
            icon = "✓" if status in ("success", "synthetic_fallback") else "⚠"
            print(f"  {icon} {class_name:<30} score={score}  status={status}")
            if status not in ("success", "synthetic_fallback"):
                all_ok = False
        except Exception as e:
            print(f"  ✗ {class_name:<30} ERROR: {e}")
            all_ok = False

    print(f"\n  Result: {'✓ All tools OK' if all_ok else '✗ Some tools failed'}")
    return all_ok


async def test_pipeline(use_agents: bool = False, verbose: bool = False):
    """Run all scoring test cases."""
    mode_label = "NEURO SAN (real LLM)" if use_agents else "SYNTHETIC (no LLM)"
    print("\n" + "=" * 60)
    print(f"Test 2 — Scoring Pipeline ({mode_label})")
    print("=" * 60)

    # Override USE_AGENTS env before importing runner
    os.environ["USE_AGENTS"] = "true" if use_agents else "false"

    from agents.runner import run_agent_pipeline, run_synthetic_pipeline

    all_passed = True

    for case in TEST_CASES:
        print(f"\n  Applicant: {case['name']}")
        print(f"  ID:        {case['applicant_id']}")
        print(f"  Consented: {case['consented_sources']}")

        try:
            if use_agents:
                result = await run_agent_pipeline(
                    case["applicant_id"],
                    case["consented_sources"],
                    case["questionnaire_answers"],
                )
            else:
                result = run_synthetic_pipeline(
                    case["applicant_id"],
                    case["consented_sources"],
                    case["questionnaire_answers"],
                )

            score = result.get("final_score", 0)
            low, high = case["expected_range"]
            passed = low <= score <= high

            print(f"  Score:     {score}/850")
            print(f"  Risk:      {result.get('risk_category', 'N/A')}")
            print(f"  Loan:      Rs {result.get('loan_recommended', 0):,}")
            print(f"  Rate:      {result.get('interest_rate', 0)}%")
            print(f"  Mode:      {result.get('pipeline_mode', 'unknown')}")
            print(f"  Expected:  {low}-{high}")
            print(f"  Result:    {'✓ PASS' if passed else '✗ FAIL'}")

            if verbose:
                breakdown = result.get("breakdown", {}) or result.get("agent_scores", {})
                if breakdown:
                    print("  Breakdown:")
                    for source, data in breakdown.items():
                        if isinstance(data, dict):
                            s = data.get("score", 0)
                            r = data.get("reason", "")
                        else:
                            s, r = data if isinstance(data, (list, tuple)) else (0, "")
                        print(f"    {source:<15} {s:>3}/100  {str(r)[:50]}")

            if not passed:
                all_passed = False

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    return all_passed


async def main():
    use_agents = "--agents" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("\n" + "="*60)
    print("  CreditBridge -- Full Pipeline Verification")
    print("="*60)

    tools_ok = await test_coded_tools()
    pipeline_ok = await test_pipeline(use_agents=use_agents, verbose=verbose)

    print("\n" + "=" * 60)
    overall = tools_ok and pipeline_ok
    print(f"Overall: {'✓ ALL TESTS PASSED' if overall else '✗ SOME TESTS FAILED'}")
    print("=" * 60)

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
