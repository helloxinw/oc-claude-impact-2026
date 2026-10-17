"""Render a PDF-converter JSON report as a self-contained HTML page.

Usage: python3 dev/src/render_report.py dev/PDF_output/R01_pdf_read/R01_pdf_read.json
Writes the HTML next to the JSON (same name, .html).
"""

import json
import sys
from html import escape
from pathlib import Path

STATUS_LABELS = {
    "documented": "Documented",
    "not_in_packet": "Not in packet",
    "contradictory": "Contradictory",
    "cannot_determine": "Can't determine",
    "not_applicable": "Not applicable",
    "redacted": "Redacted",
    "illegible": "Illegible",
}

DOC_COLORS = ["#94a3b8", "#2563eb", "#7c3aed", "#0891b2", "#16a34a",
              "#cbd5e1", "#e2e8f0", "#ea580c", "#db2777", "#65a30d"]


def e(value):
    return escape(str(value)) if value is not None else ""


def badge(status):
    return f'<span class="badge s-{e(status)}">{e(STATUS_LABELS.get(status, status))}</span>'


def pages_str(pages):
    if not pages:
        return "—"
    pages = sorted(set(pages))
    ranges, start, prev = [], pages[0], pages[0]
    for p in pages[1:]:
        if p != prev + 1:
            ranges.append(f"{start}" if start == prev else f"{start}–{prev}")
            start = p
        prev = p
    ranges.append(f"{start}" if start == prev else f"{start}–{prev}")
    return "p. " + ", ".join(ranges)


def chips(items):
    return "".join(f'<span class="chip">{e(i)}</span>' for i in items)


def section(title, body, subtitle=""):
    sub = f'<p class="sub">{e(subtitle)}</p>' if subtitle else ""
    return f'<section><h2>{e(title)}</h2>{sub}{body}</section>'


def render_patient(idx):
    pc = idx["patient_category"]
    cs = pc.get("care_setting", {})
    rr = pc.get("referral_reason", {})
    rows = [
        ("Age group", f'{e(pc.get("age_group"))} (age {e(pc.get("age"))})', pages_str(pc.get("pages"))),
        ("Criteria set", e(pc.get("criteria_set")), ""),
        ("Referral reason", e(rr.get("value")), pages_str(rr.get("pages"))),
        ("Care setting", f'{e(cs.get("value"))} {badge(cs["status"]) if cs.get("status") else ""}'
                         f'<div class="note">{e(cs.get("note"))}</div>', pages_str(cs.get("pages"))),
    ]
    body = "".join(f"<tr><th>{k}</th><td>{v}</td><td class='pg'>{p}</td></tr>" for k, v, p in rows)
    return f'<div class="card"><h3>1. Patient category</h3><table class="kv">{body}</table></div>'


def render_documents(idx, colors):
    rel = "".join(
        f"<tr><td><span class='dot' style='background:{colors.get(d['document_index'], '#999')}'></span>"
        f"{e(d['name'])}</td><td class='pg'>{pages_str(d['pages'])}</td>"
        f"<td>{chips(d.get('criteria_sections', []))}</td>"
        f"<td class='ids'>{e(', '.join(d.get('rule_ids', [])))}</td></tr>"
        for d in idx.get("relevant_documents", []))
    other = "".join(
        f"<li><span class='dot' style='background:{colors.get(d['document_index'], '#999')}'></span>"
        f"{e(d['name'])} <span class='pg'>{pages_str(d['pages'])}</span> — {e(d.get('reason'))}</li>"
        for d in idx.get("other_documents", []))
    missing = "".join(
        f"<li><b>{e(d['id'])}</b> {e(d['name'])}{(' — ' + e(d['note'])) if d.get('note') else ''}</li>"
        for d in idx.get("missing_documents", []))
    return (
        '<div class="card"><h3>2. Documents relevant to the admission criteria</h3>'
        '<table class="grid"><thead><tr><th>Document</th><th>Pages</th><th>Criteria sections</th>'
        f'<th>Rule IDs</th></tr></thead><tbody>{rel}</tbody></table>'
        '<div class="two">'
        f'<div><h4>Other documents (no criteria evidence)</h4><ul class="plain">{other or "<li>None</li>"}</ul></div>'
        f'<div><h4>Missing required documents</h4><ul class="plain missing">{missing or "<li>None</li>"}</ul></div>'
        '</div></div>')


def render_page_map(report, colors):
    names = {d["index"]: d["document_type"] for d in report["documents"]}
    tiles = "".join(
        f"<div class='tile' style='background:{colors.get(p['document_index'], '#999')}' "
        f"title='Page {p['page']}: {e(names.get(p['document_index']))} — {e(p.get('orientation'))}, "
        f"{e(p.get('quality'))}, OCR {p.get('ocr_confidence')}. {e(p.get('notes'))}'>"
        f"<span>{p['page']}</span>{'<i>↻</i>' if p.get('orientation') != 'upright' else ''}</div>"
        for p in report["pages"])
    legend = "".join(
        f"<span class='leg'><span class='dot' style='background:{colors[d['index']]}'></span>"
        f"{d['index']}: {e(d['document_type'])} ({pages_str(d['pages'])})</span>"
        for d in report["documents"])
    return section("Page map", f"<div class='tiles'>{tiles}</div><div class='legend'>{legend}</div>",
                   "One tile per page, colored by document. ↻ = scanned rotated or upside down. Hover for details.")


def render_status_summary(report):
    counts = {}
    for ce in report.get("criteria_evidence", []):
        counts[ce["status"]] = counts.get(ce["status"], 0) + 1
    order = ["documented", "contradictory", "not_in_packet", "cannot_determine", "not_applicable"]
    cells = "".join(f"<div class='stat s-{s}'><b>{counts[s]}</b>{STATUS_LABELS[s]}</div>"
                    for s in order if s in counts)
    return f"<div class='stats'>{cells}</div>"


def render_evidence(report):
    rows = []
    for ce in report.get("criteria_evidence", []):
        quotes = "".join(f"<li>“{e(q['quote'])}” <span class='pg'>p.{e(q['page'])}</span></li>"
                         for q in ce.get("evidence", []))
        rows.append(
            f"<tr class='r-{e(ce['status'])}'><td>{e(ce['section'])}</td>"
            f"<td class='ids'>{e(', '.join(ce['rule_ids']))}</td><td>{badge(ce['status'])}</td>"
            f"<td><ul class='quotes'>{quotes}</ul><div class='note'>{e(ce.get('note'))}</div></td></tr>")
    body = ("<table class='grid'><thead><tr><th>Section</th><th>Rules</th><th>Status</th>"
            f"<th>Evidence &amp; notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")
    return section("Criteria evidence", render_status_summary(report) + body,
                   "Status describes documentation only, not eligibility.")


def render_contradictions(report):
    cards = "".join(
        f"<div class='conflict'><h4>{e(c['topic'])} <span class='ids'>{e(', '.join(c['rule_ids']))}</span></h4>"
        "<ul class='quotes'>" + "".join(f"<li>“{e(i['quote'])}” <span class='pg'>p.{e(i['page'])}</span></li>"
                                        for i in c["items"]) + "</ul></div>"
        for c in report.get("contradictions", []))
    return section("Contradictions", f"<div class='conflicts'>{cards}</div>",
                   "Places where pages disagree. These often decide the case.")


def render_checklist(report):
    tiles = "".join(
        f"<div class='check r-{e(c['status'])}'><b>{e(c['id'])}</b>{badge(c['status'])}"
        f"<span class='pg'>{pages_str(c.get('pages'))}</span><div class='note'>{e(c.get('note'))}</div></div>"
        for c in report.get("referral_checklist", []))
    return section("Referral checklist (DOC-1 … DOC-10)", f"<div class='checks'>{tiles}</div>")


def render_vitals(report):
    vs = report.get("clinical_data", {}).get("vital_signs", {})
    if not vs.get("sets"):
        return ""
    rows = "".join(f"<tr><td>{e(s['time'])}</td><td>{e(s['bp'])}</td><td>{e(s['hr'])}</td><td>{e(s['temp'])}</td>"
                   f"<td>{e(s['rr'])}</td><td>{e(s['spo2'])}</td><td class='pg'>p.{e(s['page'])}</td></tr>"
                   for s in vs["sets"])
    return ("<h4>Vital signs</h4><table class='grid compact'><thead><tr><th>When</th><th>BP</th><th>HR</th>"
            f"<th>Temp</th><th>RR</th><th>SpO₂</th><th></th></tr></thead><tbody>{rows}</tbody></table>"
            f"<div class='note'>{e(vs.get('note'))}</div>")


def render_clinical(report):
    cd = report.get("clinical_data", {})
    items = []
    for key, val in cd.items():
        if key == "vital_signs" or not isinstance(val, dict):
            continue
        detail = {k: v for k, v in val.items() if k not in ("status",) and v not in (None, [], "")}
        text = "; ".join(f"{k.replace('_', ' ')}: {v if not isinstance(v, list) else len(v)}"
                         for k, v in detail.items() if not isinstance(v, (list, dict)) or k == "pages")
        items.append(f"<div class='ci r-{e(val.get('status'))}'><b>{e(key.replace('_', ' '))}</b>"
                     f"{badge(val.get('status'))}<div class='note'>{e(text)}</div></div>")
    return section("Clinical data the rules ask for", render_vitals(report) + f"<div class='cis'>{''.join(items)}</div>")


def render_flags(report):
    flags = "".join(f"<li>{e(f)}</li>" for f in report.get("flags", []))
    return section("Flags for the coordinator", f"<ul class='flags'>{flags}</ul>")


CSS = """
:root{--ink:#0f172a;--mute:#64748b;--line:#e2e8f0;--bg:#f8fafc}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg)}
header{background:#0f172a;color:#fff;padding:24px 32px}header h1{margin:0;font-size:22px}header p{margin:6px 0 0;color:#cbd5e1;max-width:900px}
main{max-width:1200px;margin:0 auto;padding:24px 32px 64px}
section,.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px 22px;margin:0 0 20px}
h2{margin:0 0 4px;font-size:17px}h3{margin:0 0 12px;font-size:16px}h4{margin:14px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
.sub{margin:0 0 14px;color:var(--mute)}.note{color:var(--mute);font-size:12.5px;margin-top:3px}
.pg{color:var(--mute);font-size:12px;white-space:nowrap}.ids{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#334155}
table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
thead th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);background:#f1f5f9}
.kv th{width:160px;color:var(--mute);font-weight:600}.compact td,.compact th{padding:5px 10px}
.chip{display:inline-block;background:#eef2ff;color:#3730a3;border-radius:999px;padding:1px 9px;margin:2px 4px 2px 0;font-size:12px}
.dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px;vertical-align:middle}
.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}.plain{list-style:none;padding:0;margin:0}.plain li{padding:4px 0}
.missing li{color:#b91c1c}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:11.5px;font-weight:600;white-space:nowrap;margin-left:6px}
.s-documented{background:#dcfce7;color:#166534}.s-not_in_packet{background:#fee2e2;color:#991b1b}
.s-contradictory{background:#fef3c7;color:#92400e}.s-cannot_determine{background:#dbeafe;color:#1e40af}
.s-not_applicable{background:#f1f5f9;color:#475569}.s-redacted{background:#1e293b;color:#fff}.s-illegible{background:#f3e8ff;color:#6b21a8}
.stats{display:flex;gap:10px;margin:0 0 14px;flex-wrap:wrap}.stat{border-radius:8px;padding:8px 14px;font-size:12.5px}.stat b{display:block;font-size:20px}
tr.r-contradictory td:first-child{box-shadow:inset 3px 0 #f59e0b}tr.r-not_in_packet td:first-child{box-shadow:inset 3px 0 #ef4444}
tr.r-not_applicable{opacity:.6}
.quotes{margin:0;padding-left:16px}.quotes li{margin:2px 0}
.tiles{display:grid;grid-template-columns:repeat(17,1fr);gap:4px}
.tile{position:relative;height:44px;border-radius:5px;color:#fff;font-weight:600;font-size:12px;display:flex;align-items:center;justify-content:center;cursor:default}
.tile i{position:absolute;top:1px;right:4px;font-style:normal;font-size:11px}
.legend{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12.5px;color:#334155}
.conflicts{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
.conflict{border:1px solid #fde68a;background:#fffbeb;border-radius:8px;padding:10px 14px}.conflict h4{margin:0 0 6px;color:#92400e;text-transform:none;letter-spacing:0;font-size:14px}
.checks,.cis{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.check,.ci{border:1px solid var(--line);border-radius:8px;padding:10px 12px}.check b,.ci b{display:block;text-transform:capitalize}
.check .badge,.ci .badge{margin:4px 0}.cis{margin-top:14px}
.flags{margin:0;padding-left:18px}.flags li{margin:4px 0}
.summary{font-size:14.5px;max-width:none}
"""


def render(report):
    docs = report["documents"]
    colors = {d["index"]: DOC_COLORS[i % len(DOC_COLORS)] for i, d in enumerate(docs)}
    pc = report["packet_index"]["patient_category"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(report['packet_id'])} – PDF converter report</title><style>{CSS}</style></head><body>
<header><h1>Packet {e(report['packet_id'])} · {e(report['page_count'])} pages · {e(pc.get('age_group'))}, {e(pc.get('age'))}</h1>
<p>{e(report.get('packet_summary'))}</p></header>
<main>
{section("Packet index", render_patient(report["packet_index"]) + render_documents(report["packet_index"], colors))}
{render_flags(report)}
{render_contradictions(report)}
{render_evidence(report)}
{render_checklist(report)}
{render_clinical(report)}
{render_page_map(report, colors)}
</main></body></html>"""


def main():
    src = Path(sys.argv[1])
    report = json.loads(src.read_text())
    out = src.with_suffix(".html")
    out.write_text(render(report))
    print(out)


if __name__ == "__main__":
    main()
