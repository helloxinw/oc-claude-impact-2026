"""Render a referral-intake decision JSON as a self-contained HTML page.

Usage: python3 dev/src/render_decision.py dev/PDF_output/R01_pdf_read/R01_intake_decision.json
Writes the HTML next to the JSON (same name, .html).
"""

import json
import sys
from pathlib import Path

from render_report import CSS, e

VERDICT_LABELS = {"met": "Met", "not_met": "Not met", "pending": "Pending (missing)", "not_applicable": "Not applicable"}
REC = {
    "approve": ("Approve", "#166534", "#dcfce7", "All applicable criteria are met and nothing is missing."),
    "deny": ("Deny", "#991b1b", "#fee2e2", "The files present show at least one criterion is not met."),
    "maybe": ("Maybe", "#92400e", "#fef3c7", "The files present meet the criteria, but required files are missing."),
}

EXTRA_CSS = """
.v-met{background:#dcfce7;color:#166534}.v-not_met{background:#fee2e2;color:#991b1b}
.v-pending{background:#fef3c7;color:#92400e}.v-not_applicable{background:#f1f5f9;color:#475569}
tr.r-not_met td:first-child{box-shadow:inset 3px 0 #ef4444}tr.r-pending td:first-child{box-shadow:inset 3px 0 #f59e0b}
tr.r-not_applicable{opacity:.55}
.banner{border-radius:12px;padding:22px 26px;margin:0 0 20px;display:flex;gap:24px;align-items:center}
.banner .rec{font-size:34px;font-weight:800;letter-spacing:.02em}
.banner p{margin:2px 0}
.disclaimer{font-size:12.5px;color:#475569;background:#f1f5f9;border-radius:8px;padding:10px 14px;margin:0 0 20px}
.reasons{margin:0;padding-left:18px}.reasons li{margin:5px 0}
.rules{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.rule{border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:12.5px}
.rule.on{border-color:#0f172a;box-shadow:0 0 0 1px #0f172a}
"""


def badge(verdict):
    return f'<span class="badge v-{e(verdict)}">{e(VERDICT_LABELS.get(verdict, verdict))}</span>'


def section(title, body, subtitle=""):
    sub = f'<p class="sub">{e(subtitle)}</p>' if subtitle else ""
    return f"<section><h2>{e(title)}</h2>{sub}{body}</section>"


def render_banner(d):
    label, fg, bg, meaning = REC[d["recommendation"]]
    esc = '<p><b>Escalate for clinical review.</b></p>' if d.get("escalate") else ""
    return (f"<div class='banner' style='background:{bg};color:{fg}'><div class='rec'>{label}</div>"
            f"<div><p><b>{e(meaning)}</b></p><p>Rule applied: {e(d.get('decision_rule_applied'))}</p>"
            f"<p>Confidence: {e(d.get('confidence'))}</p>{esc}</div></div>"
            f"<div class='disclaimer'>{e(d.get('disclaimer'))}</div>")


def render_rule_box(d):
    rec = d["recommendation"]
    boxes = "".join(f"<div class='rule{' on' if k == rec else ''}'><b>{REC[k][0]}</b><br>{e(REC[k][3])}</div>"
                    for k in ("approve", "deny", "maybe"))
    c = d.get("counts", {})
    stats = "".join(f"<div class='stat v-{k}'><b>{c.get(k, 0)}</b>{VERDICT_LABELS[k]}</div>"
                    for k in ("not_met", "pending", "met", "not_applicable"))
    return section("How the recommendation was reached", f"<div class='stats'>{stats}</div><div class='rules'>{boxes}</div>")


def render_list(title, items, subtitle=""):
    if not items:
        return ""
    return section(title, "<ul class='reasons'>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>", subtitle)


def render_items(d):
    order = {"not_met": 0, "pending": 1, "met": 2, "not_applicable": 3}
    rows = []
    for it in sorted(d.get("items", []), key=lambda i: order.get(i["verdict"], 9)):
        quotes = "".join(f"<li>“{e(q['quote'])}” <span class='pg'>p.{e(q['page'])}</span></li>"
                         for q in it.get("evidence", []))
        change = f"<div class='note'>Could change if: {e(it['could_change_if'])}</div>" if it.get("could_change_if") else ""
        rows.append(
            f"<tr class='r-{e(it['verdict'])}'><td class='ids' style='white-space:nowrap'>{e(it['item_id'])}</td>"
            f"<td><b>{e(it['name'])}</b><div class='ids'>{e(', '.join(it.get('rule_ids', [])))} · {e(it.get('rule_kind'))}</div></td>"
            f"<td>{badge(it['verdict'])}<div class='note'>checklist: {e(it.get('checklist_status'))}</div></td>"
            f"<td>{e(it.get('reason'))}<ul class='quotes'>{quotes}</ul>{change}</td></tr>")
    return section("Item-by-item verdicts",
                   "<table class='grid'><thead><tr><th>#</th><th>Item</th><th>Verdict</th><th>Reason &amp; evidence</th>"
                   f"</tr></thead><tbody>{''.join(rows)}</tbody></table>")


def render(d):
    p = d.get("patient", {})
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(d['packet_id'])} – intake recommendation</title><style>{CSS}{EXTRA_CSS}</style></head><body>
<header><h1>Packet {e(d['packet_id'])} · referral intake recommendation</h1>
<p>{e(p.get('age_group'))}, {e(p.get('age'))} · referred for {e(p.get('referral_reason'))} · care setting: {e(p.get('care_setting'))}</p></header>
<main>
{render_banner(d)}
{render_list("Why: criteria not met", d.get("not_met_reasons"))}
{render_list("Still missing", d.get("pending_requests"), "Request these from the referrer.")}
{render_list("Next steps", d.get("next_steps"))}
{render_list("Unclear rules this relies on", d.get("unclear_rules_used"))}
{render_rule_box(d)}
{render_items(d)}
{section("Patient summary", f"<p class='summary'>{e(d.get('patient_summary'))}</p>")}
</main></body></html>"""


def main():
    src = Path(sys.argv[1])
    data = json.loads(src.read_text())
    out = src.with_suffix(".html")
    out.write_text(render(data))
    print(out)


if __name__ == "__main__":
    main()
