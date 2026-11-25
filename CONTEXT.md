# fleet safety – context (read this first before helping me)

## what im building
its a laptop webcam app that catches a driver who's sleepy or using their phone, sounds an alarm
right away, logs it, and shows everything on a dashboard. free tools only, synthetic data only.

## what has to work in the demo
- detect eyes closed, yawning, looking away, and phone use
- real-time alert (sound + red text on screen)
- dashboard with at least 4 charts + 3 filters (driver, event type, date) that work on every chart
- dashboard has to open on my phone (streamlit network url)
- export the filtered data as CSV, TSV, XLSX and XML
- 30–50 fake events so the dashboard has stuff to show

## my stack (dont change these)
- apple silicone, python 3.11, venv in .venv
- opencv-contrib-python 4.11.0.86
- mediapipe==0.10.21 → use the old mp.solutions.face_mesh code, newer versions dont have it
- ultralytics YOLO, yolo26n.pt, only the COCO "cell phone" class
- sqlite (built into python) → events.db
- streamlit, plotly, pandas, openpyxl, lxml
- optional: google-genai (gemini free api, key goes in .env)
- alarm: macOS afplay in a background thread so the video doesnt freeze

## my files
src/ (the app):
- detector.py – webcam loop, settings, alert text, saves events
- detection/face_checks.py – EAR, MAR, head pose maths
- detection/alarm.py – siren sound + afplay background thread
- detection/phone_check.py – face box + "phone near face" check (YOLO itself runs in detector.py)
- severity.py – LOW/MEDIUM/HIGH rules per event type
- db.py – save_event(..., timestamp=None), get_events(), save_driving_events(), get_driving_events()
- scoring.py – driver scores from driving events
- dashboard.py – streamlit numbers, charts, filters, export
scripts/ (run by hand from the project folder, e.g. python scripts/seed.py):
- calibrate_eyes.py – shows live EAR so i can pick the threshold (was test_eyes.py)
- seed.py – 40 fake webcam events spread over the last 14 days
- driving_behavior.py + seed_behavior.py – 40 fake driving events (braking, cornering, speeding)

## events table
id, timestamp, driver_id, vehicle_id, event_type (EYES_CLOSED, YAWN, LOOK_AWAY, PHONE), duration_s, severity

## driving_events table
id, timestamp, driver_id, vehicle_id, event_type (HARSH_BRAKING, HARSH_CORNERING, SPEEDING), measured_value, threshold_value, severity

## my settings
- EAR threshold: 0.20 (eyes closed for 1.5s or more)
- MAR threshold: 0.65
- looking away: head turned more than ~25° for 2s
- alarm cooldown: 5s
- yolo: every 5th frame, phone near face for 1s or more

## how i want you to help
- send the FULL code for the whole file in a code block in the chat, not a download and not just the changed part
- explain each part simply so i can double check it
- im a beginner so keep the code simple
- when i say "wrap up", send this whole CONTEXT.md back updated in one code block:
  tick what i finished in progress, fill in any new settings (like my EAR number),
  and add a line to the session log with what we did, whats broken, and whats next

## progress
- [x] setup: venv, packages, github repo (earlysev7n/fleet-safety)
- [x] calibrate_eyes.py (was test_eyes.py) – EAR threshold set to 0.20
- [x] db.py
- [x] detector.py: eyes closed + alarm
- [x] detector.py: yawn + looking away
- [x] detector.py: phone
- [x] seed.py
- [x] dashboard.py
- [ ] tested on my phone
- [ ] gemini summary (optional)
- [x] README setup note

## session log (newest first)
- 25 nov – cleanup: split detector.py into src/detection/ (face_checks, alarm, phone_check), moved seed/calibrate scripts to scripts/ (code moved unchanged), renamed test_eyes → calibrate_eyes, seeded events now spread over 14 days (fixed the 40 rows in events.db too), trimmed requirements.txt, added .env.example + README setup. next: test on phone, gemini summary (optional)
- 23 nov – setup done: venv, packages, github repo. next: test_eyes.py