"""Build backend-like finding records from extraction + checklist + decision."""

from __future__ import annotations

from typing import Any


def build_backend_like_findings(extraction: dict[str, Any], checklist: dict[str, Any], decision: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert the hybrid pipeline output into a backend-shaped set of findings.

    This is intended to mirror the database model in backend/app/models.py while
    staying lightweight enough for the experimental prototype.
    """
    findings: list[dict[str, Any]] = []

    findings.append({
        "id": "finding-extraction-1",
        "document_id": "doc-1",
        "referral_id": "ref-1",
        "category": "extraction",
        "key": "patient_summary",
        "value": extraction["patient_summary"],
        "evidence": None,
        "rule_id": None,
        "source_page": 1,
        "verdict": None,
        "needs_verification": False,
        "verified": False,
        "override_verdict": None,
        "coordinator_note": None,
        "bbox_x0": None,
        "bbox_y0": None,
        "bbox_x1": None,
        "bbox_y1": None,
    })

    for item in checklist.get("checklist", []):
        findings.append({
            "id": f"finding-checklist-{item['item_id']}",
            "document_id": "doc-1",
            "referral_id": "ref-1",
            "category": "missing_document" if item["status"] == "missing" else "extraction",
            "key": item["item_id"],
            "value": item["reason"],
            "evidence": ", ".join(str(page) for page in item.get("found_in", [])) or None,
            "rule_id": item["rule_ids"][0] if item.get("rule_ids") else None,
            "source_page": item["found_in"][0] if item.get("found_in") else None,
            "verdict": "missing" if item["status"] == "missing" else "present",
            "needs_verification": item["status"] in {"missing", "incomplete"},
            "verified": False,
            "override_verdict": None,
            "coordinator_note": None,
            "bbox_x0": None,
            "bbox_y0": None,
            "bbox_x1": None,
            "bbox_y1": None,
        })

    findings.append({
        "id": "finding-decision-1",
        "document_id": "doc-1",
        "referral_id": "ref-1",
        "category": "decision",
        "key": "overall_decision",
        "value": decision["overall_decision"],
        "evidence": decision["overall_reasoning"],
        "rule_id": None,
        "source_page": None,
        "verdict": None,
        "needs_verification": True,
        "verified": False,
        "override_verdict": None,
        "coordinator_note": None,
        "bbox_x0": None,
        "bbox_y0": None,
        "bbox_x1": None,
        "bbox_y1": None,
    })

    findings.append({
        "id": "finding-decision-2",
        "document_id": "doc-1",
        "referral_id": "ref-1",
        "category": "decision",
        "key": "overall_reasoning",
        "value": decision["overall_reasoning"],
        "evidence": None,
        "rule_id": None,
        "source_page": None,
        "verdict": None,
        "needs_verification": True,
        "verified": False,
        "override_verdict": None,
        "coordinator_note": None,
        "bbox_x0": None,
        "bbox_y0": None,
        "bbox_x1": None,
        "bbox_y1": None,
    })

    return findings
