"""Render a customized-criteria checklist JSON as a self-contained HTML page.

Usage: python3 dev/src/render_checklist.py dev/PDF_output/R01_pdf_read/R01_custom_checklist.json
Writes the HTML next to the JSON (same name, .html).
"""

import json
import sys
from pathlib import Path

from render_report import CSS, e, pages_str

STATUS_LABELS = {
    "received": "Received",
    "incomplete": "Incomplete",
    "missing": "Missing",
    "cannot_determine": "Can't determine",
    "not_required": "Not required",
}

GROUPS = [
    ("base", "Base checklist (referral form DOC-1 … DOC-10)"),
    ("always", "Always required by the admission criteria"),
    ("triggered", "Added for this patient's conditions"),
]

EXTRA_CSS = """
.s-received{background:#dcfce7;color:#166534}.s-incomplete{background:#fef3c7;color:#92400e}
.s-missing{background:#fee2e2;color:#991b1b}.s-not_required{background:#f1f5f9;color:#475569}
.s-cannot_determine{background:#dbeafe;color:#1e40af}
tr.r-missing td:first-child{box-shadow:inset 3px 0 #ef4444}tr.r-incomplete td:first-child{box-shadow:inset 3px 0 #f59e0b}
tr.r-not_required{opacity:.55}
.prio{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#475569}
.prio.required{color:#b91c1c}
.request{counter-reset:r;list-style:none;padding:0;margin:0}
.request li{counter-increment:r;padding:8px 0 8px 36px;position:relative;border-bottom:1px solid var(--line)}
.request li:before{content:counter(r);position:absolute;left:0;top:7px;width:24px;height:24px;border-radius:50%;
  background:#0f172a;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}
.trig{border:1px solid var(--line);border-radius:8px;padding:10px 14px}
.trigs{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
"""


def badge(status):
    return f'<span class="badge s-{e(status)}">{e(STATUS_LABELS.get(status, status))}</span>'


def section(title, body, subtitle=""):
    sub = f'<p class="sub">{e(subtitle)}</p>' if subtitle else ""
    return f"<section><h2>{e(title)}</h2>{sub}{body}</section>"


def render_patient(data):
    pc = data["patient_category"]
    cs = pc.get("care_setting", {})
    care = e(cs.get("value"))
    if cs.get("status") == "contradictory":
        care += (' <span class="badge s-incomplete">Contradictory</span>'
                 f'<div class="note">Rules applied as: {e(cs.get("applied_as"))}</div>')
    rows = [
        ("Age group", f'{e(pc.get("age_group"))} (age {e(pc.get("age"))})'),
        ("Criteria set", e(data.get("criteria_set"))),
        ("Referral reason", e(pc.get("referral_reason"))),
        ("Care setting", care + f' <span class="pg">{pages_str(cs.get("pages"))}</span>'),
    ]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return section("Patient category", f'<table class="kv">{body}</table>')


def render_summary(data):
    s = data.get("summary", {})
    order = ["missing", "incomplete", "cannot_determine", "received", "not_required"]
    cells = "".join(f"<div class='stat s-{k}'><b>{s[k]}</b>{STATUS_LABELS[k]}</div>" for k in order if k in s)
    return f"<div class='stats'><div class='stat s-not_required'><b>{s.get('required', '')}</b>Required items</div>{cells}</div>"


def render_request(data):
    items = "".join(f"<li>{e(r)}</li>" for r in data.get("request_to_referrer", []))
    return section("Request to the referrer", f"<ol class='request'>{items}</ol>",
                   "Plain-language list for the hospital case manager, required items first.")


def render_checklist(data):
    out = [render_summary(data)]
    for key, title in GROUPS:
        rows = []
        for it in (i for i in data.get("checklist", []) if i.get("group") == key):
            where = "; ".join(f"doc {f['document_index']} {pages_str(f.get('pages'))}" for f in it.get("found_in", []))
            trig = f"<div class='note'>Trigger: {e(it['trigger'])}</div>" if it.get("trigger") else ""
            rows.append(
                f"<tr class='r-{e(it['status'])}'><td class='ids' style='white-space:nowrap'>{e(it['item_id'])}</td>"
                f"<td><b>{e(it['name'])}</b>{trig}</td>"
                f"<td class='ids'>{e(', '.join(it.get('rule_ids', [])))}</td>"
                f"<td><span class='prio {e(it.get('priority'))}'>{e(it.get('priority', '').replace('_', ' '))}</span></td>"
                f"<td>{badge(it['status'])}</td>"
                f"<td><span class='pg'>{e(where)}</span><div class='note'>{e(it.get('gap'))}</div></td></tr>")
        if rows:
            out.append(f"<h4>{e(title)}</h4><table class='grid'><thead><tr><th>#</th><th>Item</th><th>Rules</th>"
                       f"<th>Priority</th><th>Status</th><th>Where / gap</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")
    return section("Customized document checklist", "".join(out),
                   "Status describes documentation only, not eligibility.")


def render_triggers(data):
    fired = "".join(
        f"<div class='trig'><b>{e(t['trigger'])}</b> <span class='chip'>{e(t['section'])}</span>"
        "<ul class='quotes'>" + "".join(f"<li>“{e(q['quote'])}” <span class='pg'>p.{e(q['page'])}</span></li>"
                                        for q in t.get("evidence", [])) + "</ul>"
        f"<div class='note'>Adds: <span class='ids'>{e(', '.join(t.get('adds', [])))}</span></div></div>"
        for t in data.get("triggers", []))
    skipped = "".join(f"<li><b>{e(n['section'])}</b> — {e(n['reason'])}</li>" for n in data.get("not_triggered", []))
    return section("Why these items: triggers",
                   f"<div class='trigs'>{fired}</div><h4>Checked, not triggered</h4><ul class='plain'>{skipped}</ul>")


def render_questions(data):
    rows = "".join(f"<tr><td class='ids'>{e(', '.join(q.get('rule_ids', [])))}</td><td><b>{e(q['question'])}</b>"
                   f"<div class='note'>{e(q.get('why'))}</div></td></tr>" for q in data.get("questions", []))
    return section("Questions for the referrer",
                   f"<table class='grid'><thead><tr><th>Rules</th><th>Question</th></tr></thead><tbody>{rows}</tbody></table>")


def render(data):
    pc = data["patient_category"]
    s = data.get("summary", {})
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(data['packet_id'])} – customized checklist</title><style>{CSS}{EXTRA_CSS}</style></head><body>
<header><h1>Packet {e(data['packet_id'])} · customized document checklist</h1>
<p>{e(pc.get('age_group'))}, {e(pc.get('age'))} · referred for {e(pc.get('referral_reason'))} ·
{e(s.get('missing', 0))} missing, {e(s.get('incomplete', 0))} incomplete of {e(s.get('required', 0))} required items.
Source: {e(data.get('source_report'))}</p></header>
<main>
{render_patient(data)}
{render_request(data)}
{render_checklist(data)}
{render_questions(data)}
{render_triggers(data)}
</main></body></html>"""


def main():
    src = Path(sys.argv[1])
    data = json.loads(src.read_text())
    out = src.with_suffix(".html")
    out.write_text(render(data))
    print(out)


if __name__ == "__main__":
    main()
