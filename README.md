# Fleet safety - Driver fatigue & Distraction Detection

Detects driver fatigue and phone use from a webcam, alerts in real time, and logs events to a dashboard.

## Features

- **Camera HUD** – status bar (ATTENTIVE / DROWSY / ALERT / NO FACE), countdown rings, eye/mouth/head gauges, red pulsing border, "Logged" toast
- **Per-driver eye calibration** – 5 s at startup sets the eye limit to 75 % of your normal EAR
- **Live dashboard** – "Live now" section and charts refresh every 2 s
- **Two dashboard tabs** – *Driver monitoring* (webcam events) and *Driving behaviour* (braking, cornering, speeding)
- **Driver scores** – each driver starts at 100 and loses points per LOW / MEDIUM / HIGH event; drivers below the attention score are flagged
- **Filters + exports** – filter by driver, event type and date; download records as CSV, TSV, Excel or XML
- **Event snapshots** – a photo of each event, shown on the dashboard (`data/snapshots/`)
- **PERCLOS fatigue meter** – share of the last 60 s with eyes closed; "TAKE A BREAK" + FATIGUE event above 15 %
- **Spoken alerts** – chime for the first 2 s, then siren + a spoken warning ("Wake up. Eyes on the road.", "Put the phone down.")

## Keys (camera window)

- **C** – recalibrate (new driver)
- **Q** – quit

## Setup (Python 3.11)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put `yolo26n.pt` in `models/`. Optional: copy `.env.example` to `.env`.

## Run (from the project folder)

```bash
python scripts/seed.py            # 40 fake webcam events
python scripts/seed_behavior.py   # 40 fake driving events
python scripts/calibrate_eyes.py  # optional: check your EAR threshold
python src/detector.py            # webcam monitor, C = recalibrate, Q = quit
streamlit run src/dashboard.py
```

## Tests

```bash
python tests/test_calibration.py
python tests/test_perclos.py
python tests/test_db_snapshot.py
```

## Folders

```
src/              the app: detector, dashboard, db, severity, scoring
src/detection/    face checks (EAR/MAR/head pose), phone check, alarm, HUD
scripts/          seed data + eye calibration, run once by hand
tests/            plain-assert checks, run with python
.streamlit/       dashboard dark theme
data/             events.db + snapshots (not in git)
models/           yolo26n.pt (not in git)
```

Open the dashboard on your phone with the "Network URL" Streamlit prints (same Wi-Fi).