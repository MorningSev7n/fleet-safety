# Renders sample HUD states to PNGs and times draw_hud.
# Run from the project folder: python tests/render_hud.py [output_folder]

import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "src")
from detection.hud import draw_hud


OUT = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
OUT.mkdir(parents=True, exist_ok=True)

FACE = {"face_box": (520, 180, 760, 480), "driver_id": "DRIVER_001",
        "ear_limit": 0.20, "mar_limit": 0.65, "yaw_limit": 25}

STATES = {
    "attentive": {**FACE, "status": "ATTENTIVE", "ear": 0.29, "mar": 0.30,
                  "yaw": 4.0, "timers": {}, "alarm": False},
    "drowsy": {**FACE, "status": "DROWSY", "ear": 0.15, "mar": 0.72, "yaw": -8.0,
               "timers": {"Eyes closed": (1.1, 1.5)}, "alarm": False},
    "alert": {**FACE, "status": "ALERT", "ear": 0.27, "mar": 0.25, "yaw": 3.0,
              "timers": {"Looking away": (2.6, 2.0), "Phone": (0.4, 1.0)},
              "alarm": True, "phone_box": (800, 260, 900, 420),
              "toast": ("PHONE", 2.3, "HIGH")},
    "no_face": {"status": "NO FACE", "driver_id": "DRIVER_001", "ear": None,
                "mar": None, "yaw": None, "timers": {}, "alarm": False,
                "toast": ("EYES_CLOSED", 1.8, "MEDIUM")},
}

for name, state in STATES.items():
    frame = np.full((720, 1280, 3), 128, np.uint8)
    draw_hud(frame, state)
    assert frame.shape == (720, 1280, 3)
    cv2.imwrite(str(OUT / f"hud_{name}.png"), frame)

# Speed check: the busiest state, 100 times.
frame = np.full((720, 1280, 3), 128, np.uint8)
start = time.perf_counter()
for _ in range(100):
    draw_hud(frame, STATES["alert"])
average_ms = (time.perf_counter() - start) * 1000 / 100

print(f"PNGs in {OUT}")
print(f"draw_hud average: {average_ms:.2f} ms")
assert average_ms < 15, "HUD too slow"
print("OK")
