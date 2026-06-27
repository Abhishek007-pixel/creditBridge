"""
CashflowScoringTool — Neuro SAN CodedTool
Aggregates digital AA feeds, uploaded PDF/CSV bank statements, and manual ledgers.
Applies verification discount multipliers (AA=100%, Uploaded=85%, Ledgers=40%)
to score income and cash reserves, returning a detailed Trust Verification Matrix.

If MongoDB is empty/unavailable, falls back to the deterministic synthetic generator.
"""
import os
import sys
import asyncio
import logging
from typing import Any, Union

_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_cashflow

logger = logging.getLogger(__name__)

# ── Verification Trust Multipliers ──────────────────────────────────────────
TRUST_MULTIPLIERS = {
    "account_aggregator": 1.00,  # Digital bank feed (high trust)
    "document_uploaded":  0.85,  # PDF/CSV statement upload (medium trust)
    "self_reported":      0.40,  # Manual ledgers / screenshots (low trust)
}


def _synthetic_fallback(applicant_id: str) -> dict:
    """Fallback to legacy synthetic data logic if no files or feeds found."""
    try:
        data = generate_applicant_data(applicant_id)
        cashflow_data = data["cashflow"]
        score, reason = score_cashflow(cashflow_data)

        # Map synthetic structure
        return {
            "source": "cashflow",
            "applicant_id": applicant_id,
            "final_cashflow_score": score,
            "reason": reason + " (synthetic fallback — no real statements connected)",
            "metrics": {
                "average_monthly_balance": cashflow_data["avg_monthly_balance"],
                "monthly_credits": cashflow_data["avg_monthly_balance"] * 1.5,
                "bounced_transactions_count": cashflow_data["bounced_transactions"],
                "regular_credits_flag": cashflow_data["credit_regularity"] == "Regular",
                "savings_behavior": cashflow_data["savings_behavior"]
            },
            "trust_matrix": {
                "account_aggregator_pct": 0.0,
                "document_uploaded_pct": 0.0,
                "self_reported_pct": 100.0,  # treat as self-reported
                "trust_description": "100% Synthetic data used"
            },
            "data_source": "synthetic",
            "status": "synthetic_fallback"
        }
    except Exception as e:
        return {
            "source": "cashflow",
            "applicant_id": applicant_id,
            "final_cashflow_score": 40,
            "reason": f"Fallback error: {str(e)[:80]}",
            "data_source": "error",
            "status": "error"
        }


class CashflowScoringTool(CodedTool):
    """
    Evaluates cashflow stability and verification level.
    Aggregates all digital feeds and manual statements from MongoDB.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "cashflow",
                "error": "No applicant_id provided",
                "final_cashflow_score": 40,
                "reason": "Missing applicant ID",
                "status": "error",
            }

        try:
            from database_mongo import (
                is_mongo_available,
                get_mongo_db,
                get_aa_feeds_for_applicant,
                get_bank_statements_for_applicant
            )

            if not is_mongo_available():
                return _synthetic_fallback(applicant_id)

            db = get_mongo_db()

            # 1. Fetch connected AA bank feeds
            aa_feeds = await get_aa_feeds_for_applicant(applicant_id)
            
            # 2. Fetch processed bank statements PDF/CSV
            statements = await get_bank_statements_for_applicant(applicant_id)
            scored_statements = [s for s in statements if s.get("stage") == "scored"]

            if not aa_feeds and not scored_statements:
                return _synthetic_fallback(applicant_id)

            # 3. Collect all transactions with their verification levels
            all_txs = []
            
            # AA feeds
            for feed in aa_feeds:
                level = feed.get("verification_level", "account_aggregator")
                for tx in feed.get("transactions", []):
                    tx["verification_level"] = level
                    all_txs.append(tx)

            # Uploaded PDF/CSV statements
            # Note: We must query the database to get the actual transactions (since list view excludes them)
            from bson import ObjectId
            for stmt in scored_statements:
                level = stmt.get("verification_level", "document_uploaded")
                full_stmt = await db.bank_statements.find_one({"_id": ObjectId(stmt["_id"])})
                if full_stmt:
                    for tx in full_stmt.get("transactions", []):
                        tx["verification_level"] = level
                        all_txs.append(tx)

            if not all_txs:
                return _synthetic_fallback(applicant_id)

            # 4. Perform calculations
            total_credits = 0.0
            total_debits = 0.0
            weighted_credits = 0.0
            bounces = 0
            
            # Track volume of transactions per verification level for trust matrix
            volume_by_level = {"account_aggregator": 0.0, "document_uploaded": 0.0, "self_reported": 0.0}

            for tx in all_txs:
                amount = float(tx.get("amount") or 0.0)
                txt_type = tx.get("type", "debit").lower()
                level = tx.get("verification_level", "self_reported")
                
                # Check for bounced transactions in description (e.g. bounce, insufficient, penalty)
                desc = tx.get("description", "").lower()
                if "bounce" in desc or "insufficient" in desc or "chq return" in desc or "penalty" in desc:
                    bounces += 1

                multiplier = TRUST_MULTIPLIERS.get(level, 0.40)
                volume_by_level[level] += amount

                if txt_type == "credit":
                    total_credits += amount
                    weighted_credits += amount * multiplier
                else:
                    total_debits += amount

            # Compute verification percentages
            total_volume = sum(volume_by_level.values())
            if total_volume == 0:
                total_volume = 1.0
            aa_pct = round((volume_by_level["account_aggregator"] / total_volume) * 100, 1)
            doc_pct = round((volume_by_level["document_uploaded"] / total_volume) * 100, 1)
            self_pct = round((volume_by_level["self_reported"] / total_volume) * 100, 1)

            # Calculate metrics (assuming 6 months window for averages)
            months = 6
            avg_credits = total_credits / months
            avg_weighted_credits = weighted_credits / months
            
            # Simple balance estimation: credits - debits (minimum baseline ₹10,000)
            avg_balance = max(10000.0, (total_credits - total_debits) / months)
            
            # 5. Core score calculation (0 - 100)
            # Base score: derived from average weighted credits
            # Target credits ₹40,000/mo = max 45 points
            credit_score_fraction = min(avg_weighted_credits / 40000.0, 1.0)
            score = credit_score_fraction * 45.0

            # Balance score: derived from average monthly balance
            # Target balance ₹15,000/mo = max 35 points
            balance_score_fraction = min(avg_balance / 15000.0, 1.0)
            score += balance_score_fraction * 35.0

            # Stability bonus: regular transaction flow count = max 20 points
            stability_bonus = min(len(all_txs) / 20.0, 1.0) * 20.0
            score += stability_bonus

            # Penalties: deduct 15 points per bounced transaction
            score -= bounces * 15.0
            
            # Clamp final score
            final_score = min(100, max(0, round(score)))

            # Build summary reason
            source_labels = []
            if aa_pct > 0: source_labels.append(f"{aa_pct}% AA")
            if doc_pct > 0: source_labels.append(f"{doc_pct}% PDF statement")
            if self_pct > 0: source_labels.append(f"{self_pct}% Manual ledger")
            source_desc = " + ".join(source_labels)

            reason = (
                f"Monthly credits ₹{avg_credits:,.0f} (weighted: ₹{avg_weighted_credits:,.0f}). "
                f"Avg balance ₹{avg_balance:,.0f}. "
                f"Trust matrix: {source_desc}. "
            )
            if bounces > 0:
                reason += f"Warning: {bounces} bounced transaction(s) detected."
            else:
                reason += "No transaction bounces detected."

            return {
                "source": "cashflow",
                "applicant_id": applicant_id,
                "final_cashflow_score": final_score,
                "reason": reason,
                "metrics": {
                    "average_monthly_balance": round(avg_balance, 0),
                    "monthly_credits": round(avg_credits, 0),
                    "monthly_weighted_credits": round(avg_weighted_credits, 0),
                    "bounced_transactions_count": bounces,
                    "transaction_count": len(all_txs),
                },
                "trust_matrix": {
                    "account_aggregator_pct": aa_pct,
                    "document_uploaded_pct": doc_pct,
                    "self_reported_pct": self_pct,
                    "trust_description": f"Verified: {aa_pct}% AA, {doc_pct}% Doc Uploads, {self_pct}% Ledgers"
                },
                "data_source": "mongodb",
                "status": "success"
            }

        except Exception as e:
            # Safe fallback if error
            logger.error(f"Cashflow tool invocation error: {e}")
            fallback = _synthetic_fallback(applicant_id)
            fallback["tool_error"] = str(e)[:150]
            fallback["status"] = "error_fallback"
            return fallback
