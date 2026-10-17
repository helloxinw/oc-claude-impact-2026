"""Build the pipeline run summary from every packet folder under PDF_output.

Usage: python3 dev/src/render_index.py dev/PDF_output
Writes dev/PDF_output/index.html and dev/PDF_output/pipeline_run.json.
"""

import json
import sys
from pathlib import Path

from render_report import CSS, e

REC_STYLE = {"approve": "v-met", "deny": "v-not_met", "maybe": "v-pending"}

EXTRA_CSS = """
.v-met{background:#dcfce7;color:#166534}.v-not_met{background:#fee2e2;color:#991b1b}
.v-pending{background:#fef3c7;color:#92400e}.v-error{background:#f1f5f9;color:#475569}
.rec{font-weight:700;text-transform:uppercase;letter-spacing:.04em}
a{color:#2563eb;text-decoration:none}a:hover{text-decoration:underline}
.links a{margin-right:12px;white-space:nowrap}
"""


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def collect(root):
    rows = []
    for folder in sorted(root.glob("*_pdf_read")):
        pid = folder.name[: -len("_pdf_read")]
        stages = {
            "pdf_read": folder / f"{pid}_pdf_read.json",
            "custom_checklist": folder / f"{pid}_custom_checklist.json",
            "intake_decision": folder / f"{pid}_intake_decision.json",
        }
        data = {k: load(p) for k, p in stages.items()}
        decision = data["intake_decision"] or {}
        missing = [k for k, v in data.items() if v is None]
        pc = (data["pdf_read"] or {}).get("packet_index", {}).get("patient_category", {})
        top = (decision.get("not_met_reasons") or decision.get("pending_requests") or [""])[0]
        rows.append({
            "packet_id": pid,
            "recommendation": decision.get("recommendation", "error"),
            "confidence": decision.get("confidence"),
            "escalate": decision.get("escalate", False),
            "counts": decision.get("counts", {}),
            "age": pc.get("age"),
            "referral_reason": (pc.get("referral_reason") or {}).get("value"),
            "top_reason": top,
            "error": f"missing or invalid: {', '.join(missing)}" if missing else None,
            "pages": {k: f"{folder.name}/{p.with_suffix('.html').name}" for k, p in stages.items()
                      if p.with_suffix(".html").exists()},
        })
    return rows


def render(rows):
    totals = {}
    for r in rows:
        totals[r["recommendation"]] = totals.get(r["recommendation"], 0) + 1
    stats = "".join(f"<div class='stat {REC_STYLE.get(k, 'v-error')}'><b>{totals.get(k, 0)}</b>{k.title()}</div>"
                    for k in ("approve", "deny", "maybe", "error"))
    body = []
    for r in rows:
        c = r["counts"]
        cls = REC_STYLE.get(r["recommendation"], "v-error")
        esc = " <span class='badge v-pending'>Escalate</span>" if r["escalate"] else ""
        links = "".join(f"<a href='{e(href)}'>{label}</a>" for key, label in
                        (("pdf_read", "Packet report"), ("custom_checklist", "Checklist"), ("intake_decision", "Recommendation"))
                        if (href := r["pages"].get(key)))
        detail = e(r["error"]) if r["error"] else e(r["top_reason"])
        body.append(
            f"<tr><td><b>{e(r['packet_id'])}</b></td>"
            f"<td><span class='badge {cls} rec'>{e(r['recommendation'])}</span>{esc}"
            f"<div class='note'>confidence: {e(r['confidence'])}</div></td>"
            f"<td>{e(r['age'])}<div class='note'>{e(r['referral_reason'])}</div></td>"
            f"<td class='ids'>{c.get('not_met', 0)} not met · {c.get('pending', 0)} pending · {c.get('met', 0)} met</td>"
            f"<td>{detail}</td><td class='links'>{links}</td></tr>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Referral intake – pipeline run</title><style>{CSS}{EXTRA_CSS}</style></head><body>
<header><h1>Referral intake pipeline · {len(rows)} packet(s)</h1>
<p>Recommendations only. IHH staff make the final admission decision.</p></header>
<main><section><h2>Results</h2><div class='stats'>{stats}</div>
<table class='grid'><thead><tr><th>Packet</th><th>Recommendation</th><th>Age / reason</th><th>Items</th>
<th>Top reason or first request</th><th>Pages</th></tr></thead><tbody>{''.join(body)}</tbody></table></section></main></body></html>"""


def main():
    root = Path(sys.argv[1])
    rows = collect(root)
    (root / "pipeline_run.json").write_text(json.dumps({"packets": rows}, indent=2))
    (root / "index.html").write_text(render(rows))
    print(root / "index.html")


if __name__ == "__main__":
    main()
