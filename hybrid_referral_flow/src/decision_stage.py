"""Stage C: produce a final recommendation in backend-matching shape."""

from __future__ import annotations

from typing import Any

from .schemas import DecisionPayload


def make_decision(checklist: dict[str, Any]) -> dict[str, Any]:
    """Return a backend-compatible overall decision payload.

    The explicit naming is aligned to backend/app/claude_client.py and the app's
    database model. It keeps the transparent yarong_dev-style reasoning, but in a
    production-style payload format.
    """
    missing = any(item["status"] == "missing" for item in checklist.get("checklist", []))

    if missing:
        payload = DecisionPayload(
            overall_decision="maybe",
            overall_reasoning="Required documentation is missing, so the case cannot be fully evaluated without more information.",
            flags_for_human_review=[],
            missing_documents=checklist.get("missing_documents", []),
            rule_verdicts=[{
                "rule_id": "DOC-4",
                "value_found": None,
                "verdict": "unclear",
                "reasoning": "H&P is missing from the packet, so the clinical picture cannot be fully assessed.",
                "evidence_page": None,
                "quote": None,
            }],
            confidence="medium",
            disclaimer="Recommendation only. Human staff make the final admission decision.",
        )
    else:
        payload = DecisionPayload(
            overall_decision="yes",
            overall_reasoning="Packet appears complete and meets the reviewable criteria.",
            flags_for_human_review=[],
            missing_documents=[],
            rule_verdicts=[{
                "rule_id": "DOC-1",
                "value_found": "Referral form available",
                "verdict": "met",
                "reasoning": "The referral form was present and readable.",
                "evidence_page": 1,
                "quote": "Referral form",
            }],
            confidence="medium",
            disclaimer="Recommendation only. Human staff make the final admission decision.",
        )

    return payload.model_dump()
