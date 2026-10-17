# Hybrid Referral Intake Experiment

This folder is a third, separate prototype that combines the strengths of both approaches:

- The transparent, staged reasoning of the legacy `yarong_dev` workflow
- The production-ready structure of the `backend` app

The goal is to keep the app/database layer as the system of record, while reusing the clearer clinical decision logic from the original pipeline.

## Design goal

The hybrid method is:

1. Extract facts from the PDF the same way the backend does
2. Use the yarong_dev-style stages to reason through evidence and missing items
3. Generate a structured decision payload suitable for the backend database
4. Keep intermediate explainability artifacts for human review

## Folder structure

```text
hybrid_referral_flow/
├── README.md
├── architecture.md
├── src/
│   ├── __init__.py
│   ├── extraction_stage.py
│   ├── checklist_stage.py
│   ├── decision_stage.py
│   └── pipeline.py
└── outputs/
    └── .gitkeep
```

## Hybrid flow

```text
PDF upload
  ↓
OCR + page extraction (backend style)
  ↓
Stage A: extract evidence (yarong_dev style)
  ↓
Stage B: build patient-specific checklist
  ↓
Stage C: compute approve / deny / maybe
  ↓
Persist to backend-compatible decision model
  ↓
Show evidence + allow coordinator override
```

## Key idea

The backend remains the source of truth for storage and app behavior, while the legacy reasoning flow is kept as a structured decision engine for:

- packet evidence extraction
- rule-by-rule review
- missing document requests
- final recommendation explanation

## Intended use

This folder is meant for experimental work only. It should not replace the live backend app, but it can be used to test whether the hybrid model produces clearer and more auditable decisions.

## Suggested next steps

- port the yarong_dev decision rules into `src/checklist_stage.py`
- map extracted fields into backend-friendly JSON
- use the backend `Finding` / `Referral` concepts as output format
- compare hybrid outputs against legacy `yarong_dev` outputs for consistency
