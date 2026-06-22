"""
CreditBridge Agent Runner
Handles communication between FastAPI and the Neuro SAN agent network.

Two modes:
  USE_AGENTS=true  → runs real Neuro SAN pipeline
  USE_AGENTS=false → runs synthetic fallback (always works, good for demo)

The synthetic fallback is kept permanently as a safety net.
If the agent pipeline fails for any reason, it falls back automatically.
"""
import os
import sys
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Add parent directory to path so coded tools can import from data/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import USE_AGENTS, AGENT_MANIFEST_FILE, AGENT_TOOL_PATH, MISTRAL_API_KEY
from data.synthetic_generator import (
    generate_applicant_data,
    score_phone_bill,
    score_ecommerce,
    score_geolocation,
    score_merchant,
    score_cashflow,
    score_psychometric,
    calculate_final_score,
)
from database import get_agent_weights


def run_synthetic_pipeline(
    applicant_id: str,
    consented_sources: list[str],
    questionnaire_answers: list[int],
) -> dict:
    """
    Synthetic scoring pipeline — always works, deterministic.
    Used when USE_AGENTS=false or as fallback if agent pipeline fails.
    """
    weights = get_agent_weights()
    data = generate_applicant_data(applicant_id)

    agent_scores = {}

    if "phone_bill" in consented_sources:
        score, reason = score_phone_bill(data["phone_bill"])
        agent_scores["phone_bill"] = (score, reason)

    if "ecommerce" in consented_sources:
        score, reason = score_ecommerce(data["ecommerce"])
        agent_scores["ecommerce"] = (score, reason)

    if "geolocation" in consented_sources:
        score, reason = score_geolocation(data["geolocation"])
        agent_scores["geolocation"] = (score, reason)

    # Psychometric always runs (questionnaire, not a data API)
    score, reason = score_psychometric(questionnaire_answers)
    agent_scores["psychometric"] = (score, reason)

    if "merchant" in consented_sources:
        score, reason = score_merchant(data["merchant"])
        agent_scores["merchant"] = (score, reason)

    if "cashflow" in consented_sources:
        score, reason = score_cashflow(data["cashflow"])
        agent_scores["cashflow"] = (score, reason)

    # Ensure psychometric weight is always active
    all_active = list(agent_scores.keys())
    active_weights = {k: v for k, v in weights.items() if k in all_active}

    result = calculate_final_score(agent_scores, active_weights, all_active)
    result["pipeline_mode"] = "synthetic"
    result["applicant_id"] = applicant_id
    return result


async def run_agent_pipeline(
    applicant_id: str,
    consented_sources: list[str],
    questionnaire_answers: list[int],
) -> dict:
    """
    Neuro SAN agent pipeline.
    Starts the agent server, calls credit_coordinator, returns result.
    Falls back to synthetic if anything fails.
    """
    if not USE_AGENTS:
        logger.info("USE_AGENTS=false, using synthetic pipeline")
        return run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)

    if not MISTRAL_API_KEY:
        logger.warning("No MISTRAL_API_KEY set, falling back to synthetic pipeline")
        return run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)

    try:
        # Set environment variables for Neuro SAN
        os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY
        os.environ["AGENT_MANIFEST_FILE"] = AGENT_MANIFEST_FILE
        os.environ["AGENT_TOOL_PATH"] = AGENT_TOOL_PATH

        # Import Neuro SAN client
        from neuro_san.client.agent_session import AgentSession

        session = AgentSession(
            agent_name="creditbridge",
            connection_type="direct",
        )

        # Build the prompt for the coordinator
        prompt = json.dumps({
            "applicant_id": applicant_id,
            "consented_sources": consented_sources,
            "questionnaire_answers": questionnaire_answers,
        })

        response = session.chat(prompt)

        # Parse response
        if isinstance(response, str):
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("Could not extract JSON from agent response")
        elif isinstance(response, dict):
            result = response
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")

        result["pipeline_mode"] = "neuro_san"
        result["applicant_id"] = applicant_id
        logger.info(f"Agent pipeline completed for {applicant_id}, score={result.get('final_score')}")
        return result

    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}. Falling back to synthetic.")
        result = run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)
        result["pipeline_mode"] = "synthetic_fallback"
        result["fallback_reason"] = str(e)
        return result
