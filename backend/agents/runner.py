"""
CreditBridge Agent Runner
Bridges FastAPI routes and the Neuro SAN agent network.

Two modes controlled by USE_AGENTS env var:
  true  — real Neuro SAN pipeline (requires API key)
  false — synthetic fallback (always works, no key needed)

The synthetic fallback is ALWAYS available as a safety net.
If the agent pipeline fails for any reason, it falls back automatically.
This means the demo NEVER breaks.
"""
import os
import sys
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Ensure backend root is on path
_runner_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.abspath(os.path.join(_runner_dir, ".."))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from config import (
    USE_AGENTS,
    AGENT_MANIFEST_FILE,
    AGENT_TOOL_PATH,
    AGENT_MODEL_NAME,
    get_active_api_key,
)
from data.synthetic_generator import (
    generate_applicant_data,
    score_phone_bill,
    score_ecommerce,
    score_geolocation,
    score_merchant,
    score_cashflow,
    score_psychometric,
    score_financial_commitment,
    calculate_final_score,
)
from database import get_agent_weights


def run_synthetic_pipeline(
    applicant_id: str,
    consented_sources: list,
    questionnaire_answers: list,
) -> dict:
    """
    Pure synthetic scoring pipeline.
    Always deterministic, always works, no API key needed.
    Used when USE_AGENTS=false or as automatic fallback.

    Accepts both 'phone_bill' (legacy) and 'bill_consistency' (new)
    as consent source names — both map to the bill consistency score.
    """
    weights = get_agent_weights()
    data = generate_applicant_data(applicant_id)
    agent_scores = {}

    # bill_consistency replaces phone_bill — accept both names for backward compat
    has_bill_consent = (
        "bill_consistency" in consented_sources or
        "phone_bill" in consented_sources
    )
    if has_bill_consent:
        s, r = score_phone_bill(data["phone_bill"])
        # Store under bill_consistency key (canonical)
        agent_scores["bill_consistency"] = (s, r)

    if "ecommerce" in consented_sources:
        s, r = score_ecommerce(data["ecommerce"])
        agent_scores["ecommerce"] = (s, r)

    if "geolocation" in consented_sources:
        s, r = score_geolocation(data["geolocation"])
        agent_scores["geolocation"] = (s, r)

    # Psychometric always runs
    s, r = score_psychometric(questionnaire_answers)
    agent_scores["psychometric"] = (s, r)

    if "merchant" in consented_sources:
        s, r = score_merchant(data["merchant"])
        if s >= 0:
            agent_scores["merchant"] = (s, r)

    if "cashflow" in consented_sources:
        s, r = score_cashflow(data["cashflow"])
        agent_scores["cashflow"] = (s, r)

    if "financial_commitment" in consented_sources:
        s, r = score_financial_commitment(data["financial_commitment"])
        agent_scores["financial_commitment"] = (s, r)

    # Update weights to use bill_consistency key
    updated_weights = {}
    for k, v in weights.items():
        if k == "phone_bill":
            updated_weights["bill_consistency"] = v
        else:
            updated_weights[k] = v

    active_weights = {k: v for k, v in updated_weights.items() if k in agent_scores}
    result = calculate_final_score(agent_scores, active_weights, list(agent_scores.keys()))
    result["pipeline_mode"] = "synthetic"
    result["applicant_id"] = applicant_id
    return result


async def run_agent_pipeline(
    applicant_id: str,
    consented_sources: list,
    questionnaire_answers: list,
) -> dict:
    """
    Neuro SAN agent pipeline (real LLM).
    Falls back to synthetic automatically on any failure.
    """
    if not USE_AGENTS:
        logger.info("USE_AGENTS=false — using synthetic pipeline")
        return run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)

    env_var_name, api_key = get_active_api_key()
    if not api_key:
        logger.warning("No LLM API key found — falling back to synthetic pipeline")
        result = run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)
        result["pipeline_mode"] = "synthetic_no_key"
        return result

    try:
        # Set API key in environment for Neuro SAN
        os.environ[env_var_name] = api_key

        # Set GOOGLE_API_KEY as alias if using Gemini
        if "gemini" in AGENT_MODEL_NAME.lower():
            os.environ["GOOGLE_API_KEY"] = api_key

        os.environ["AGENT_MANIFEST_FILE"] = AGENT_MANIFEST_FILE
        os.environ["AGENT_TOOL_PATH"] = AGENT_TOOL_PATH

        # Build prompt for the coordinator
        prompt = json.dumps({
            "applicant_id": applicant_id,
            "consented_sources": consented_sources,
            "questionnaire_answers": questionnaire_answers,
        }, ensure_ascii=False)

        logger.info(f"Starting Neuro SAN pipeline for applicant {applicant_id}")
        logger.info(f"Model: {AGENT_MODEL_NAME}, Manifest: {AGENT_MANIFEST_FILE}")

        # Import Neuro SAN — use direct_agent_session_factory (v0.6.x API)
        from neuro_san.client.direct_agent_session_factory import DirectAgentSessionFactory

        import asyncio
        from neuro_san.client.streaming_input_processor import StreamingInputProcessor

        factory = DirectAgentSessionFactory()
        session = factory.create_session(
            agent_name="creditbridge",
        )

        input_processor = StreamingInputProcessor(session=session)
        processor = input_processor.get_message_processor()
        request = input_processor.formulate_chat_request(prompt)

        def run_sync_chat():
            for chat_response in session.streaming_chat(request):
                message = chat_response.get("response", {})
                processor.process_message(message, chat_response.get("type"))
            return processor.get_compiled_answer()

        response_text = await asyncio.to_thread(run_sync_chat)


        # Parse JSON from response
        if isinstance(response_text, dict):
            result = response_text
        else:
            import re
            json_match = re.search(r'\{[\s\S]*\}', str(response_text))
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"No JSON found in agent response: {str(response_text)[:200]}")

        result["pipeline_mode"] = "neuro_san"
        result["applicant_id"] = applicant_id
        logger.info(f"Neuro SAN pipeline complete. Score: {result.get('final_score')}")
        return result

    except ImportError as e:
        logger.error(f"Neuro SAN import error: {e}")
        result = run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)
        result["pipeline_mode"] = "synthetic_fallback"
        result["fallback_reason"] = f"import_error: {str(e)}"
        return result

    except Exception as e:
        logger.error(f"Neuro SAN pipeline failed: {e}. Falling back to synthetic.")
        result = run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)
        result["pipeline_mode"] = "synthetic_fallback"
        result["fallback_reason"] = str(e)[:200]
        return result
