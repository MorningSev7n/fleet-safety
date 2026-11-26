# Fleet Safety – Driver Fatigue & Distraction Detection

A laptop webcam watches the driver. If they close their eyes, yawn, look away or pick up a phone, the app sounds an alarm and speaks a warning. Each event is saved with a photo and appears on a live dashboard, which you can also open on a phone.

**Who it's for:** an SME fleet owner who can't ride along with every driver. The dashboard shows who is tired or distracted, when it happens and how serious it is, so the owner knows which drivers need coaching.

All data is synthetic, and every tool used is free and open source.

---

## What you need

- A **Mac or Windows** laptop with a webcam. It's tested on Mac. Windows support is new and hasn't been tested yet, so please report whether the alarm sounds.
- **Python 3.11**. Mac: check with `python3.11 --version`, and if it's missing, run `brew install python@3.11`. Windows: install it from python.org, then check with `py -3.11 --version`.
- Internet access the first time, to install packages and download the phone-detection model (5 MB).

## Setup (one time, about 5 minutes)

```bash
git clone https://github.com/MorningSev7n/fleet-safety.git
cd fleet-safety
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On **Windows**, replace the two venv lines with:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
```

Download the YOLO phone-detection model into `models/`:

```bash
python -c "from ultralytics import YOLO; YOLO('models/yolo26n.pt')"
```

You don't need a `.env` file. `.env.example` is for an optional Gemini feature that isn't used yet.

## Run

Every new terminal starts the same way:

```bash
cd fleet-safety
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

**1. Load demo data** (run once only: `seed.py` adds 40 more events every time it runs):

```bash
python scripts/seed.py
python scripts/seed_behavior.py
```

This adds 40 fake webcam events and 40 fake driving events (braking, cornering, speeding).

**2. Start the webcam monitor** (terminal 1):

```bash
python src/detector.py
```

The first time, your computer asks for camera access. Allow it, then run the command again if needed.
For the first 5 seconds, look at the camera normally while it calibrates to your eyes.

| Key | Action |
|---|---|
| **C** | Recalibrate (a new driver sits down) |
| **Q** | Quit |

**3. Start the dashboard** (terminal 2):

```bash
streamlit run src/dashboard.py
```

The first time, Streamlit asks for an email in the terminal. Just press **Enter** to skip.
It opens in your browser. To view it on a phone, open the **Network URL** that Streamlit prints. The phone must be on the same Wi-Fi.

## Try it (demo flow)

1. Close your eyes for about 1.5 seconds. You hear a chime, then a siren and "Wake up. Eyes on the road."
2. Hold a phone up near your face. It's flagged as PHONE with the warning "Put the phone down."
3. Yawn, or turn your head away. These are flagged too.
4. On the dashboard, the event shows under **Live now** within about 3 seconds, with its photo.
5. **Driver monitoring** tab: webcam events by day and by type, KPIs, records and export.
6. **Driving behaviour** tab: driver scores (start at 100, minus points per event), events by type and by day.
7. Filter by driver, event type or date. Every chart updates. Download the records as CSV, TSV, Excel or XML.

## Features

- **Fatigue and distraction detection:** eyes closed (eye aspect ratio), yawning, head turned away, phone use (YOLO)
- **Per-driver calibration:** sets the eye limit to 75% of your normal eye openness, so glasses and narrow eyes work
- **PERCLOS fatigue meter:** the share of the last 60 seconds with eyes closed. Above 15%, it shows "TAKE A BREAK" and logs a FATIGUE event
- **Real-time alert:** a chime for the first 2 seconds, then a siren and a spoken warning
- **Camera HUD:** shows the status (ATTENTIVE / DROWSY / ALERT / NO FACE), countdown rings, gauges, and a confirmation each time an event is logged
- **Live dashboard:** 4 charts, 3 filters, driver scores, event photos, and export to 4 formats

## Troubleshooting

| Problem | Fix |
|---|---|
| Black window or "could not open camera" | Mac: System Settings → Privacy & Security → Camera → turn on Terminal (or your editor). Windows: Settings → Privacy & security → Camera → allow desktop apps. Then restart the terminal |
| Alerts fire too easily or not at all | Press **C** to recalibrate. Sit facing the camera in good light |
| No sound | Check the volume and that it isn't muted |
| Phone can't open the dashboard | Use the **Network URL**, not the Local one, with both devices on the same Wi-Fi |
| `Could not load YOLO model` | Run the model download command from Setup again |
| Dashboard is empty | Run the two `seed` scripts |

## Tests

```bash
python tests/test_calibration.py
python tests/test_perclos.py
python tests/test_db_snapshot.py
python tests/test_alarm_commands.py
```

## Folders

```
src/              the app: detector, dashboard, database, severity, scoring
src/detection/    face checks, phone check, alarm, HUD
scripts/          demo data + eye-calibration check (run by hand)
tests/            plain-assert checks, run with python
.streamlit/       dashboard dark theme
data/             events.db + snapshots (created on first run, not in git)
models/           yolo26n.pt (downloaded in Setup, not in git)
```

## Free stack

Python, OpenCV, MediaPipe Face Mesh, Ultralytics YOLO, SQLite, Streamlit, Plotly, and pandas, all run locally.
