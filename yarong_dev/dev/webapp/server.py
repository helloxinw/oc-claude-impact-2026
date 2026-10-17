"""Referral intake web portal.

Upload a packet PDF; the server runs dev/agents/referral_intake_pipeline.md
headless with the Claude Code CLI and serves the resulting pages.

Usage: python3 dev/webapp/server.py [--port 8000]
Then open http://127.0.0.1:8000
"""

import argparse
import cgi
import json
import mimetypes
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
PACKETS_DIR = ROOT / "PDF_files"
OUTPUT_DIR = ROOT / "dev" / "PDF_output"
MAX_UPLOAD = 60 * 1024 * 1024
PACKET_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
MAX_CONCURRENT = 2

STAGES = [
    ("pdf_read", "Read & extract PDF", "pdf-converter.md"),
    ("custom_checklist", "Build custom checklist", "customized_creteria_agent.md"),
    ("intake_decision", "Recommend approve / deny / maybe", "referral_intake_output.md"),
]

ALLOWED_TOOLS = "Read Write Edit Glob Grep Agent Bash(python3 *)"
DISALLOWED_TOOLS = "Read(referral-intake-resource/eval/**) Bash(python3 *decisions.json*)"

jobs = {}
jobs_lock = threading.Lock()
slots = threading.Semaphore(MAX_CONCURRENT)


def stage_file(pid, key):
    return OUTPUT_DIR / f"{pid}_pdf_read" / f"{pid}_{key}.json"


def valid_json(path):
    try:
        json.loads(path.read_text())
        return True
    except (OSError, ValueError):
        return False


def stage_states(pid, since=0.0, running=False):
    """done / running / pending per stage, ignoring files older than `since`."""
    states, active_set = [], False
    for key, label, agent in STAGES:
        f = stage_file(pid, key)
        fresh = f.exists() and f.stat().st_mtime >= since and valid_json(f)
        if fresh:
            state = "done"
        elif running and not active_set:
            state, active_set = "running", True
        else:
            state = "pending"
        states.append({"key": key, "label": label, "agent": agent, "state": state})
    return states


def describe(event):
    """Turn one stream-json event into a short activity line, or None."""
    if event.get("type") == "assistant":
        lines = []
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                inp = block.get("input", {})
                detail = (inp.get("description") or inp.get("file_path") or inp.get("command")
                          or inp.get("pattern") or "")
                lines.append(f"{block.get('name')}: {str(detail)[:140]}")
            elif block.get("type") == "text" and block.get("text", "").strip():
                lines.append(block["text"].strip().splitlines()[0][:200])
        return lines
    if event.get("type") == "result":
        return [f"Finished: {str(event.get('result', ''))[:200]}"]
    return None


def run_pipeline(pid, force):
    job = jobs[pid]
    with slots:
        job.update(status="running", started=time.time())
        prompt = (
            "Run the referral intake pipeline. Follow dev/agents/referral_intake_pipeline.md exactly, "
            f'with inputs: packet_ids: ["{pid}"], packets_dir: "PDF_files/", force: {str(force).lower()}. '
            "Never open referral-intake-resource/eval/decisions.json. "
            f"When finished, reply with one line: {pid} – <recommendation> (<confidence>)."
        )
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits",
               "--allowedTools", ALLOWED_TOOLS, "--disallowedTools", DISALLOWED_TOOLS]
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)
        except FileNotFoundError:
            job.update(status="error", error="The 'claude' CLI was not found on PATH.", finished=time.time())
            return
        job["pid_proc"] = proc.pid
        for raw in proc.stdout:
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines = describe(json.loads(raw))
            except ValueError:
                lines = [raw[:200]]
            for line in lines or []:
                job["events"].append({"t": round(time.time() - job["started"]), "text": line})
                del job["events"][:-200]
        code = proc.wait()
        decision = stage_file(pid, "intake_decision")
        if decision.exists() and decision.stat().st_mtime >= job["since"] and valid_json(decision):
            job["status"] = "done"
            subprocess.run(["python3", "dev/src/render_index.py", "dev/PDF_output"], cwd=ROOT,
                           capture_output=True)
        else:
            job.update(status="error", error=f"Pipeline exited (code {code}) without a valid intake decision.")
        job["finished"] = time.time()


def packet_summary(pid):
    d = stage_file(pid, "intake_decision")
    if not valid_json(d):
        return None
    data = json.loads(d.read_text())
    return {"packet_id": pid, "recommendation": data.get("recommendation"),
            "confidence": data.get("confidence"), "counts": data.get("counts", {}),
            "updated": d.stat().st_mtime}


class Handler(BaseHTTPRequestHandler):
    server_version = "ReferralIntake/1.0"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not path.is_file():
            return self.send_json({"error": "not found"}, 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self.send_file(STATIC / "index.html")
        if path == "/api/packets":
            found = [s for s in (packet_summary(f.name[: -len("_pdf_read")])
                                 for f in sorted(OUTPUT_DIR.glob("*_pdf_read"))) if s]
            with jobs_lock:
                active = [pid for pid, j in jobs.items() if j["status"] in ("queued", "running")]
            return self.send_json({"packets": found, "active": active})
        m = re.fullmatch(r"/api/jobs/([A-Za-z0-9_-]+)", path)
        if m:
            pid = m.group(1)
            job = jobs.get(pid)
            if not job:
                done = packet_summary(pid)
                return self.send_json({"packet_id": pid, "status": "done" if done else "none",
                                       "stages": stage_states(pid), "events": []})
            elapsed = (job.get("finished") or time.time()) - (job.get("started") or time.time())
            return self.send_json({
                "packet_id": pid, "status": job["status"], "error": job.get("error"),
                "elapsed": round(elapsed), "events": job["events"][-40:],
                "stages": stage_states(pid, job["since"], job["status"] == "running")})
        m = re.fullmatch(r"/api/packets/([A-Za-z0-9_-]+)/decision", path)
        if m:
            f = stage_file(m.group(1), "intake_decision")
            return self.send_file(f) if valid_json(f) else self.send_json({"error": "no decision yet"}, 404)
        if path.startswith("/output/"):
            target = (OUTPUT_DIR / path[len("/output/"):]).resolve()
            if OUTPUT_DIR.resolve() not in target.parents:
                return self.send_json({"error": "forbidden"}, 403)
            return self.send_file(target)
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/packets":
            return self.send_json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_UPLOAD:
            return self.send_json({"error": "Upload must be a PDF under 60 MB."}, 400)
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers["Content-Type"]})
        item = form["file"] if "file" in form else None
        if item is None or not item.filename:
            return self.send_json({"error": "No file uploaded."}, 400)
        data = item.file.read()
        if not data.startswith(b"%PDF"):
            return self.send_json({"error": "That file is not a PDF."}, 400)
        pid = Path(item.filename).stem.strip()
        if not PACKET_ID.match(pid):
            return self.send_json({"error": "File name must be letters, numbers, - or _ (e.g. R02.pdf)."}, 400)
        force = form.getfirst("force", "false") == "true"
        with jobs_lock:
            if pid in jobs and jobs[pid]["status"] in ("queued", "running"):
                return self.send_json({"packet_id": pid, "status": "running", "note": "Already running."})
            if not force and packet_summary(pid):
                return self.send_json({"packet_id": pid, "status": "done",
                                       "note": "Results already exist. Tick 're-run' to run again."})
            PACKETS_DIR.mkdir(exist_ok=True)
            (PACKETS_DIR / f"{pid}.pdf").write_bytes(data)
            # On re-run only files written from now count; otherwise the pipeline reuses passing stages.
            since = time.time() - 1 if force else 0.0
            jobs[pid] = {"status": "queued", "events": [], "since": since, "started": None}
        threading.Thread(target=run_pipeline, args=(pid, force), daemon=True).start()
        self.send_json({"packet_id": pid, "status": "queued"}, 202)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Referral intake portal on http://127.0.0.1:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
