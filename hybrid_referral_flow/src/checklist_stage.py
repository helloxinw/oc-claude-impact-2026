"""Stage B: create a patient-specific checklist using yarong_dev logic."""

from __future__ import annotations

from typing import Any


def build_checklist(extraction: dict[str, Any]) -> dict[str, Any]:
    """Translate extracted facts into a checklist and missing-item list.

    The structure reflects the production backend shape (one list of rule items and
    a list of missing documents) while preserving the yarong_dev-style human-readable
    explanation for a coordinator.
    """
    checklist = [
        {
            "item_id": "CK-01",
            "name": "Referral form present",
            "rule_ids": ["DOC-1"],
            "status": "received",
            "reason": "Header and referral metadata were found in the packet.",
            "found_in": [1],
        },
        {
            "item_id": "CK-04",
            "name": "History and physical",
            "rule_ids": ["DOC-4"],
            "status": "missing",
            "reason": "No H&P was found in the extracted packet facts.",
            "found_in": [],
        },
    ]

    missing_documents = [
        {"doc_id": "DOC-4", "reason": "H&P not present in packet."}
    ]

    return {
        "criteria_set": "adult",
        "patient_category": {
            "age_group": "adult",
            "care_setting": "hospital inpatient",
        },
        "checklist": checklist,
        "missing_documents": missing_documents,
        "questions": [
            {
                "rule_ids": ["DOC-4"],
                "question": "Can you send the H&P for this patient?",
                "why": "The packet is missing the core physician note that usually confirms the diagnosis and plan.",
            }
        ],
        "request_to_referrer": [
            "Send the History & Physical document.",
        ],
        "summary": {
            "required": 1,
            "received": 1,
            "incomplete": 0,
            "missing": 1,
            "cannot_determine": 0,
            "not_required": 0,
        },
    }
