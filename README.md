# Fleet safety - Driver fatigue & Distraction Detection

Detects driver fatigue and phone use from a webcam, alerts in real time, and logs events to a dashboard.

## Setup (macOS, Apple silicon, Python 3.11)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put `yolo26n.pt` in `models/`. Optional: copy `.env.example` to `.env` and add your Gemini key.

## Run (from the project folder)

```bash
python scripts/seed.py            # 40 fake webcam events
python scripts/seed_behavior.py   # 40 fake driving events
python scripts/calibrate_eyes.py  # optional: check your EAR threshold
python src/detector.py            # webcam monitor, press Q to quit
streamlit run src/dashboard.py
```

## Folders

```
src/              the app: detector, dashboard, db, severity, scoring
src/detection/    face checks (EAR/MAR/head pose), phone check, alarm
scripts/          seed data + eye calibration, run once by hand
data/             events.db (not in git)
models/           yolo26n.pt (not in git)
```

Open the dashboard on your phone with the "Network URL" Streamlit prints (same Wi-Fi).
