from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import DigitalTwin
from server.vision import VISION


VENUE_PATH = ROOT / "venue" / "venue_graph.json"
DASHBOARD_DIR = ROOT / "dashboard"
TICK_INTERVAL_S = 1.0
SIM_DT_S = 10
FORECAST_HORIZON_TICKS = 6

_lock = threading.Lock()
_twin = DigitalTwin(str(VENUE_PATH), dt_s=SIM_DT_S, horizon_ticks=FORECAST_HORIZON_TICKS)
_latest_state = _twin.state()
_running = True


def _tick_loop():
    global _latest_state
    while _running:
        with _lock:
            vision = VISION.status()
            if vision["running"] and vision["calibrated_occupancy"]:
                _twin.ingest_vision_observation(
                    vision["zone_id"],
                    vision["calibrated_occupancy"],
                )
            _latest_state = _twin.tick()
            _latest_state["vision"] = vision
        time.sleep(TICK_INTERVAL_S)


def _reset():
    global _twin, _latest_state
    with _lock:
        _twin = DigitalTwin(str(VENUE_PATH), dt_s=SIM_DT_S, horizon_ticks=FORECAST_HORIZON_TICKS)
        _latest_state = _twin.state()
        _latest_state["vision"] = VISION.status()


CONTENT_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, payload: dict, code: int = 200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/vision/upload":
            query = parse_qs(parsed.query)
            profile = query.get("profile", ["north_grandstand"])[0]
            threshold = int(query.get("threshold", ["25"])[0])
            scale = int(query.get("scale", ["80"])[0])

            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 300 * 1024 * 1024:
                self._send_json({"ok": False, "error": "Invalid or oversized upload."}, 400)
                return

            data = self.rfile.read(length)
            suffix = Path(query.get("filename", ["upload.mp4"])[0]).suffix or ".mp4"
            VISION.configure(profile, threshold, scale)
            self._send_json(VISION.start(data, suffix=suffix))
            return

        if parsed.path == "/api/vision/stop":
            VISION.stop()
            self._send_json({"ok": True})
            return

        self.send_error(404)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/state":
            with _lock:
                self._send_json(_latest_state)
            return

        if parsed.path == "/api/vision/status":
            self._send_json(VISION.status())
            return

        if parsed.path == "/api/vision/stream":
            self._stream_mjpeg()
            return

        if parsed.path == "/api/reset":
            _reset()
            self._send_json({"ok": True})
            return

        if parsed.path in ("/", "/index.html"):
            self._send_file(DASHBOARD_DIR / "index.html")
            return

        clean = parsed.path.lstrip("/")
        candidate = DASHBOARD_DIR / clean
        if candidate.resolve().parent == DASHBOARD_DIR.resolve() and candidate.exists():
            self._send_file(candidate)
            return

        self.send_error(404)

    def _stream_mjpeg(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        last_frame = None
        try:
            while True:
                frame = VISION.frame()
                if frame and frame != last_frame:
                    self.wfile.write(
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Cache-Control: no-cache\r\n\r\n" +
                        frame +
                        b"\r\n"
                    )
                    self.wfile.flush()
                    last_frame = frame
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError):
            return


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    t = threading.Thread(target=_tick_loop, daemon=True)
    t.start()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Digital twin running -> http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        global _running
        _running = False
        VISION.stop()


if __name__ == "__main__":
    main()
