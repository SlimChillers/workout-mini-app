#!/usr/bin/env python3
"""
Workout Logger Webhook Server.

Receives workout data via HTTP POST from the Telegram Mini App
and writes it to Google Sheets. Runs independently of Hermes.
"""

import json
import logging
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [workout] %(message)s")
logger = logging.getLogger("workout-webhook")

SPREADSHEET_ID = "1REsqKFnvUgejcXHU1EVCGJVr8WLm89qgp4423PhwTLo"
GAPI = "/opt/data/google-venv/bin/python /opt/data/profiles/coding-premium/skills/productivity/google-workspace/scripts/google_api.py"
PORT = 8920


class WorkoutHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - %s", self.client_address[0], format % args)

    def do_POST(self):
        if self.path != "/log":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._respond(400, {"ok": False, "error": "Invalid JSON"})
            return

        if data.get("type") != "workout_log":
            self._respond(400, {"ok": False, "error": "Unknown type"})
            return

        try:
            result = self._log_to_sheets(data)
            self._respond(200, result)
        except Exception as e:
            logger.error("Failed: %s", e)
            self._respond(500, {"ok": False, "error": str(e)})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"ok": True, "status": "healthy"})
        else:
            self.send_error(404)

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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
            raise RuntimeError(result.stderr or result.stdout or "Unknown error")

        exercise_names = [r[2] for r in rows]
        summary = ", ".join(exercise_names)
        msg = f"✅ {date} — {workout}\n💪 {summary}"
        if cardio_type and cardio_min:
            msg += f"\n🏃 {cardio_type} {cardio_min}min"

        logger.info("Logged %d rows for %s", len(rows), date)
        return {"ok": True, "logged": len(rows), "message": msg}


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), WorkoutHandler)
    logger.info("Workout webhook listening on http://0.0.0.0:%d/log", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()
