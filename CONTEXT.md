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
- detector.py – webcam, eye/mouth/head checks, yolo phone check, alarm, saves events
- db.py – save_event(driver_id, vehicle_id, event_type, duration_s, severity) and get_events() → dataframe
- seed.py – makes 40 fake events
- dashboard.py – streamlit numbers, 4 charts, filters, export

## events table
id, timestamp, driver_id, vehicle_id, event_type (EYES_CLOSED, YAWN, LOOK_AWAY, PHONE), duration_s, severity

## my settings
- EAR threshold: ____ (eyes closed for 1.5s or more)
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
- [ ] test_eyes.py (EAR open: __ closed: __)
- [ ] db.py
- [ ] detector.py: eyes closed + alarm
- [ ] detector.py: yawn + looking away
- [ ] detector.py: phone
- [ ] seed.py
- [ ] dashboard.py
- [ ] tested on my phone
- [ ] gemini summary (optional)
- [ ] README setup note

## session log (newest first)
- 23 nov – setup done: venv, packages, github repo. next: test_eyes.py