"""Run the hybrid referral intake pipeline end-to-end."""

from __future__ import annotations

from typing import Any

from .checklist_stage import build_checklist
from .decision_stage import make_decision
from .extraction_stage import extract_packet
from .finding_builder import build_backend_like_findings


def run_hybrid_pipeline(pages: list[str]) -> dict[str, Any]:
    """Prototype entry point for the hybrid method.

    This preserves the yarong_dev-style step order while outputting backend-like
    decision and finding structures for easier integration into the final app.
    """
    extraction = extract_packet(pages)
    checklist = build_checklist(extraction)
    decision = make_decision(checklist)
    findings = build_backend_like_findings(extraction, checklist, decision)

    return {
        "referral": {
            "id": "ref-1",
            "status": "needs_info" if decision["overall_decision"] == "maybe" else "ready_for_review",
            "ai_decision": decision["overall_decision"],
            "ai_decision_summary": decision["overall_reasoning"],
        },
        "extraction": extraction,
        "checklist": checklist,
        "decision": decision,
        "findings": findings,
    }


if __name__ == "__main__":
    sample_pages = [
        "Referral form: patient admitted for evaluation",
        "Progress note: no H&P attached",
    ]
    result = run_hybrid_pipeline(sample_pages)
    print(result)
