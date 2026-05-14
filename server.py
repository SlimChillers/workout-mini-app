#!/usr/bin/env python3
"""
Combined Mini App server: serves the workout HTML AND handles /log webhook.
One Cloudflare tunnel covers both.
"""

import json
import logging
import os
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [workout] %(message)s")
logger = logging.getLogger("workout-server")

SPREADSHEET_ID = "1REsqKFnvUgejcXHU1EVCGJVr8WLm89qgp4423PhwTLo"
GAPI = "/opt/data/google-venv/bin/python /opt/data/profiles/coding-premium/skills/productivity/google-workspace/scripts/google_api.py"
PORT = 8920
HTML_DIR = "/opt/data/workout-mini-app"


class WorkoutServer(SimpleHTTPRequestHandler):
    """Serves static files from HTML_DIR and handles /log POST."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HTML_DIR, **kwargs)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.client_address[0], format % args)

    def do_POST(self):
        if self.path != "/log":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "Invalid JSON"})
            return

        if payload.get("type") != "workout_log":
            self._json(400, {"ok": False, "error": "Unknown type"})
            return

        try:
            result = self._log_to_sheets(payload)
            self._json(200, result)
        except Exception as e:
            logger.error("Sheet write failed: %s", e)
            self._json(500, {"ok": False, "error": str(e)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _log_to_sheets(self, data):
        date = data.get("date", "")
        workout = data.get("workout", "")
        exercises = data.get("exercises", [])
        cardio_type = data.get("cardio_type", "")
        cardio_min = data.get("cardio_min", 0)
        notes = data.get("notes", "")

        rows = []
        for ex in exercises:
            if ex.get("skipped"):
                continue
            rows.append([
                date, workout, ex["name"],
                str(ex["weight"]) if ex.get("weight", 0) > 0 else "",
                str(ex["reps"]) if ex.get("reps", 0) > 0 else "",
                str(ex["sets"]) if ex.get("sets", 0) > 0 else "",
                cardio_type,
                str(cardio_min) if cardio_min > 0 else "",
                notes
            ])

        if not rows and (cardio_type or cardio_min):
            rows.append([date, workout, "Cardio only", "", "", "",
                         cardio_type, str(cardio_min), notes])
        elif rows and (cardio_type or cardio_min):
            rows[-1][6] = cardio_type
            rows[-1][7] = str(cardio_min)

        if not rows:
            return {"ok": True, "logged": 0, "message": "Nothing to log"}

        values_json = json.dumps(rows)
        cmd = f'{GAPI} sheets append {SPREADSHEET_ID} "Log!A:I" --values \'{values_json}\''

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15,
            env={**os.environ, "HOME": os.path.expanduser("~")}
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Server error")

        names = [r[2] for r in rows]
        msg = f"✅ {date} — {workout}\n💪 {', '.join(names)}"
        if cardio_type and cardio_min:
            msg += f"\n🏃 {cardio_type} {cardio_min}min"

        logger.info("Logged %d rows for %s", len(rows), date)
        return {"ok": True, "logged": len(rows), "message": msg}


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), WorkoutServer)
    logger.info("Serving mini app + webhook on http://0.0.0.0:%d", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
