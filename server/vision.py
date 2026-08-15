from __future__ import annotations

import threading
import time
import tempfile
from pathlib import Path
from dataclasses import asdict

try:
    import cv2
except Exception:
    cv2 = None

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


PROFILES = {
    "north_grandstand": {
        "zone_id": "grandstand_n",
        "label": "NORTH GRANDSTAND CAMERA",
        "recommendation": "DIVERT FLOW → EXIT 2 (MAIN) via PADDOCK CLUB",
        "direction": "DOWN + RIGHT",
    },
    "south_grandstand": {
        "zone_id": "grandstand_s",
        "label": "SOUTH GRANDSTAND CAMERA",
        "recommendation": "DIVERT FLOW → EXIT 2 (MAIN) via PADDOCK CLUB",
        "direction": "UP + RIGHT",
    },
    "main_concourse": {
        "zone_id": "concourse_1",
        "label": "MAIN CONCOURSE CAMERA",
        "recommendation": "DIVERT FLOW → EXIT 1 (NORTH) / EXIT 3 (SOUTH)",
        "direction": "SPLIT FLOW",
    },
}


class VisionMonitor:
    """
    Lightweight live-video perception service for the hackathon demo.

    It uses YOLO person tracking on a selected video file, renders annotated
    frames as MJPEG, and exposes a calibrated venue-zone observation that can
    be injected into the digital twin.

    `persons_per_detection` is intentionally explicit: a CCTV camera samples
    only part of a physical zone, so raw detections are not equivalent to
    total venue occupancy without calibration.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.error = ""
        self.video_path: Path | None = None
        self.profile = "north_grandstand"
        self.threshold = 25
        self.persons_per_detection = 80
        self.latest_jpeg: bytes | None = None
        self.detected_people = 0
        self.calibrated_occupancy = 0
        self.fps = 0.0
        self.frame_index = 0
        self.alert = False
        self.recommendation = ""
        self.direction = ""
        self.zone_id = "grandstand_n"
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._model = None

    def configure(self, profile: str, threshold: int, persons_per_detection: int) -> None:
        if profile not in PROFILES:
            profile = "north_grandstand"
        with self.lock:
            self.profile = profile
            self.threshold = max(1, int(threshold))
            self.persons_per_detection = max(1, int(persons_per_detection))
            cfg = PROFILES[profile]
            self.zone_id = cfg["zone_id"]
            self.recommendation = cfg["recommendation"]
            self.direction = cfg["direction"]

    def start(self, data: bytes, suffix: str = ".mp4") -> dict:
        if cv2 is None or YOLO is None:
            msg = (
                "Vision dependencies are not installed. Run: "
                "pip install -r requirements-vision.txt"
            )
            with self.lock:
                self.error = msg
            return {"ok": False, "error": msg}

        self.stop()
        suffix = suffix if suffix.startswith(".") else f".{suffix}"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.close()

        with self.lock:
            self.video_path = Path(tmp.name)
            self.error = ""
            self.frame_index = 0
            self.detected_people = 0
            self.calibrated_occupancy = 0
            self.alert = False
            self.running = True
            self._stop.clear()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return {"ok": True}

    def stop(self) -> None:
        self._stop.set()
        with self.lock:
            self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _load_model(self):
        if self._model is None:
            self._model = YOLO("yolov8n.pt")

    def _run(self) -> None:
        cap = None
        try:
            self._load_model()
            with self.lock:
                path = str(self.video_path)
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                raise RuntimeError("Could not open uploaded video.")

            source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            last_t = time.perf_counter()

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                result = self._model.track(
                    frame,
                    persist=True,
                    conf=0.25,
                    classes=[0],
                    verbose=False,
                )[0]

                count = int(len(result.boxes)) if result.boxes is not None else 0
                annotated = result.plot()

                with self.lock:
                    self.frame_index += 1
                    self.detected_people = count
                    self.calibrated_occupancy = count * self.persons_per_detection
                    self.alert = count >= self.threshold
                    cfg = PROFILES[self.profile]
                    self.recommendation = cfg["recommendation"]
                    self.direction = cfg["direction"]

                    now = time.perf_counter()
                    elapsed = now - last_t
                    if elapsed > 0:
                        self.fps = 0.8 * self.fps + 0.2 * (1.0 / elapsed)
                    last_t = now

                    label = (
                        f"{cfg['label']}  |  PEOPLE: {count}  |  "
                        f"VENUE OCCUPANCY ≈ {self.calibrated_occupancy:,}  | "
                        f"CALIBRATION ×{self.persons_per_detection}"
                    )
                    cv2.rectangle(annotated, (12, 12), (annotated.shape[1] - 12, 56), (10, 16, 21), -1)
                    cv2.putText(
                        annotated, label, (22, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 212, 255), 2,
                        cv2.LINE_AA
                    )

                    if self.alert:
                        action = f"ALERT → {self.recommendation} | {self.direction}"
                        cv2.rectangle(
                            annotated,
                            (12, annotated.shape[0] - 70),
                            (annotated.shape[1] - 12, annotated.shape[0] - 12),
                            (48, 18, 15), -1
                        )
                        cv2.putText(
                            annotated, action[:110],
                            (22, annotated.shape[0] - 34),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 230, 255), 2,
                            cv2.LINE_AA
                        )
                    else:
                        cv2.putText(
                            annotated,
                            f"TRACK CLEAR  |  Trigger at >= {self.threshold} detections",
                            (22, annotated.shape[0] - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.56, (0, 230, 120), 2,
                            cv2.LINE_AA
                        )

                ok, encoded = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ok:
                    with self.lock:
                        self.latest_jpeg = encoded.tobytes()

                time.sleep(max(0.0, 0.02 if source_fps > 0 else 0.04))

        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.running = False
        finally:
            if cap is not None:
                cap.release()

    def status(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "error": self.error,
                "profile": self.profile,
                "profile_label": PROFILES[self.profile]["label"],
                "zone_id": self.zone_id,
                "detected_people": self.detected_people,
                "calibrated_occupancy": self.calibrated_occupancy,
                "threshold": self.threshold,
                "persons_per_detection": self.persons_per_detection,
                "fps": round(self.fps, 1),
                "alert": self.alert,
                "recommendation": self.recommendation,
                "direction": self.direction,
                "frame": self.frame_index,
            }

    def frame(self) -> bytes | None:
        with self.lock:
            return self.latest_jpeg


VISION = VisionMonitor()
