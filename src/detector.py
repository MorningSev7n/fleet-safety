
import cv2
import mediapipe as mp
import os
import statistics
import time

from collections import deque
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO

from db import save_event
from severity import classify_severity
from detection.face_checks import (
    get_landmark_points,
    eye_aspect_ratio,
    calculate_mar,
    estimate_head_pose,
    calibrate_threshold,
    update_perclos,
    is_fatigued,
)
from detection.alarm import (
    ALARM_SOUND,
    alarm_active,
    create_alarm_sound,
    play_chime,
    set_alarm,
    start_alarm_worker,
    stop_alarm_worker,
)
from detection.phone_check import get_face_box, phone_near_face
from detection.hud import draw_hud


# ==========================================
# 1. SETTINGS
# ==========================================

CAMERA_INDEX = 0

DRIVER_ID = "DRIVER_001"
VEHICLE_ID = "VEHICLE_001"

# Eye detection
EAR_THRESHOLD = 0.20  # default, used only if calibration fails
CALIBRATION_SECONDS = 5.0
EYES_CLOSED_SECONDS = 1.5

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Yawn detection
MAR_THRESHOLD = 0.65
YAWN_SECONDS = 1.0


# Looking-away detection
LOOK_AWAY_ANGLE = 25
LOOK_AWAY_SECONDS = 2.0

# Phone detection
ROOT = Path(__file__).resolve().parent.parent
YOLO_MODEL = str(ROOT / "models" / "yolo26n.pt")
YOLO_FRAME_INTERVAL = 5
PHONE_SECONDS = 1.0
PHONE_CLASS_ID = 67
PHONE_CONFIDENCE = 0.35

# Display
WINDOW_NAME = "Fleet Safety - Driver Monitoring"

# Event snapshots (small JPEGs shown on the dashboard)
SNAPSHOT_FOLDER = ROOT / "data" / "snapshots"
SNAPSHOT_WIDTH = 480

# Raw camera frame kept per event type, from when its alert fired.
# finish_event takes it out again, so each picture belongs to one event.
snapshots = {}


# ==========================================
# 2. EVENT LOGGING
# ==========================================

def save_snapshot(frame, timestamp, event_type):
    """
    Save a small JPEG of the frame.
    Returns its path relative to the project folder, or None.
    """

    if frame is None:
        return None

    try:

        SNAPSHOT_FOLDER.mkdir(parents=True, exist_ok=True)

        # Colons are not allowed in Windows file names.
        file_name = f"{timestamp.replace(':', '-')}_{event_type}.jpg"
        path = SNAPSHOT_FOLDER / file_name

        height, width = frame.shape[:2]
        small = cv2.resize(
            frame,
            (SNAPSHOT_WIDTH, int(height * SNAPSHOT_WIDTH / width))
        )

        if not cv2.imwrite(str(path), small):
            raise OSError("cv2.imwrite failed")

        return str(path.relative_to(ROOT))

    except Exception as error:

        # The event is still saved, just without a picture.
        print(f"Could not save snapshot for {event_type}: {error}")
        return None


def log_event(event_type, duration, frame=None):
    """
    Classify and save an event using its full duration.
    frame is the raw camera picture from when the alert fired (or None).
    """

    severity = classify_severity(
        event_type,
        duration
    )

    if severity == "UNKNOWN":

        print(
            f"EVENT NOT SAVED: {event_type} "
            f"({duration:.2f} seconds)"
        )

        return None

    try:

        # Same time for the database row and the picture's file name.
        timestamp = datetime.now().isoformat(timespec="seconds")

        save_event(
            DRIVER_ID,
            VEHICLE_ID,
            event_type,
            round(duration, 2),
            severity,
            timestamp=timestamp,
            snapshot=save_snapshot(frame, timestamp, event_type)
        )

        print(
            f"EVENT SAVED: {event_type} | "
            f"{duration:.2f} seconds | "
            f"Severity: {severity}"
        )

        # The HUD shows this as a "Logged: ..." toast.
        return (event_type, duration, severity)

    except Exception as error:

        print(
            f"Database error while saving {event_type}: {error}"
        )

        return None


def finish_event(event_type, start_time, end_time):
    """
    Finalize an event when the detected behavior ends.

    Events shorter than their minimum duration are ignored.
    Returns (event_type, duration, severity) if saved, else None.
    """

    # The event is over, so its picture is used now or never.
    frame = snapshots.pop(event_type, None)

    if start_time is None:
        return None

    duration = end_time - start_time

    if classify_severity(event_type, duration) != "UNKNOWN":
        return log_event(event_type, duration, frame)

    return None


# ==========================================
# 3. DISPLAY HELPERS
# ==========================================

def draw_eye_points(frame, points):

    for point in points:

        cv2.circle(
            frame,
            point,
            3,
            (0, 255, 0),
            -1
        )



# ==========================================
# 4. MAIN DETECTOR
# ==========================================

def run_detector():

    print("Starting Fleet Safety Driver Monitoring...")
    print("Press Q to quit, C to calibrate again.")

    # Generate the emergency siren.
    try:

        create_alarm_sound()

    except Exception as error:

        print(f"Could not generate alarm sound: {error}")
        return

    alarm_thread = start_alarm_worker()

    # Open webcam.
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():

        print("ERROR: Could not open webcam.")
        stop_alarm_worker(alarm_thread)
        return

    # Load YOLO.
    try:

        print(f"Loading YOLO model: {YOLO_MODEL}")
        yolo_model = YOLO(YOLO_MODEL)

    except Exception as error:

        print(f"ERROR: Could not load YOLO model: {error}")

        cap.release()
        stop_alarm_worker(alarm_thread)

        return

    mp_face_mesh = mp.solutions.face_mesh

    # Event timing.
    eyes_closed_start = None
    yawn_start = None
    look_away_start = None
    phone_start = None

    # PERCLOS: (time, eyes_closed) for the last 60 s.
    perclos_history = deque()
    perclos = None
    fatigue_start = None

    # YOLO frame tracking.
    frame_count = 0
    phone_detected = False
    phone_box_to_draw = None

    # Last saved event, shown as a toast for a few seconds.
    toast = None
    toast_time = 0.0

    # Eye calibration runs first; C starts it again.
    # calibration_start = None means "start a fresh calibration now".
    calibrating = True
    calibration_start = None
    calibration_tries = 1
    ear_samples = []
    ear_limit = EAR_THRESHOLD
    limit_note = None

    try:

        with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:

            while True:

                success, frame = cap.read()

                if not success:

                    print("ERROR: Could not read webcam.")
                    break

                frame = cv2.flip(frame, 1)

                # Clean copy for snapshots (eye dots and HUD are drawn on frame).
                raw_frame = frame.copy()

                height, width, _ = frame.shape
                current_time = time.monotonic()

                # Reset alert states every frame.
                eyes_alert_active = False
                look_away_alert_active = False
                phone_alert_active = False

                # Events saved this frame (for the HUD toast).
                saved_events = []

                # HUD readings (stay None when there is no face).
                average_ear = None
                mar = None
                yaw = None
                eyes_closed = False
                yawning = False

                # ----------------------------------
                # FACE DETECTION
                # ----------------------------------

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                face_results = face_mesh.process(rgb_frame)

                face_detected = bool(
                    face_results.multi_face_landmarks
                )

                face_box = None

                if face_detected:

                    face_landmarks = (
                        face_results.multi_face_landmarks[0]
                    )

                    face_box = get_face_box(
                        face_landmarks,
                        width,
                        height
                    )

                    # ----------------------------------
                    # EYE DETECTION
                    # ----------------------------------

                    left_points = get_landmark_points(
                        face_landmarks,
                        LEFT_EYE,
                        width,
                        height
                    )

                    right_points = get_landmark_points(
                        face_landmarks,
                        RIGHT_EYE,
                        width,
                        height
                    )

                    left_ear = eye_aspect_ratio(left_points)
                    right_ear = eye_aspect_ratio(right_points)

                    average_ear = (
                        left_ear + right_ear
                    ) / 2.0

                    draw_eye_points(frame, left_points)
                    draw_eye_points(frame, right_points)

                # ----------------------------------
                # CALIBRATION (no detection, no events, no alarm)
                # ----------------------------------

                if calibrating:

                    alarm_active.clear()

                    if calibration_start is None:
                        calibration_start = current_time
                        calibration_tries = 1
                        ear_samples = []

                    if face_detected:
                        ear_samples.append(average_ear)

                    progress = min(
                        (current_time - calibration_start) / CALIBRATION_SECONDS,
                        1.0
                    )

                    if progress >= 1.0:

                        new_limit = calibrate_threshold(ear_samples)

                        if new_limit is not None:

                            ear_limit = new_limit
                            limit_note = (
                                f"Baseline {statistics.median(ear_samples):.2f}"
                                f" → limit {new_limit:.2f}"
                            )
                            calibrating = False

                        elif calibration_tries == 1:

                            # One more try before giving up.
                            calibration_tries = 2
                            calibration_start = current_time
                            ear_samples = []

                        else:

                            ear_limit = EAR_THRESHOLD
                            limit_note = "Using default limit"
                            calibrating = False

                        if not calibrating:
                            print(f"Calibration: {limit_note}")

                    if calibration_tries == 1:
                        message = "Look at the camera normally – calibrating"
                    else:
                        message = "Calibration unclear, look at the camera"

                    draw_hud(frame, {
                        "status": "CALIBRATING",
                        "driver_id": DRIVER_ID,
                        "face_box": face_box,
                        "calibration": (progress, message),
                    })

                    cv2.imshow(WINDOW_NAME, frame)

                    key = cv2.waitKey(1) & 0xFF

                    if key == ord("q"):
                        break

                    if key == ord("c"):
                        calibration_start = None

                    continue

                if face_detected:

                    eyes_closed = average_ear < ear_limit

                    if eyes_closed:

                        if eyes_closed_start is None:
                            eyes_closed_start = current_time

                        closed_duration = (
                            current_time - eyes_closed_start
                        )

                        if closed_duration >= EYES_CLOSED_SECONDS:

                            eyes_alert_active = True
                            # setdefault keeps the frame from the first alert frame.
                            snapshots.setdefault("EYES_CLOSED", raw_frame)

                    else:

                        saved_events.append(finish_event(
                            "EYES_CLOSED",
                            eyes_closed_start,
                            current_time
                        ))

                        eyes_closed_start = None

                    perclos = update_perclos(
                        perclos_history,
                        current_time,
                        eyes_closed
                    )

                    # ----------------------------------
                    # YAWN DETECTION
                    # ----------------------------------

                    mar = calculate_mar(
                        face_landmarks,
                        width,
                        height
                    )

                    yawning = mar > MAR_THRESHOLD

                    if yawning:

                        if yawn_start is None:
                            yawn_start = current_time
                            snapshots["YAWN"] = raw_frame

                    else:

                        saved_events.append(finish_event(
                            "YAWN",
                            yawn_start,
                            current_time
                        ))

                        yawn_start = None

                    # ----------------------------------
                    # LOOKING-AWAY DETECTION
                    # ----------------------------------

                    yaw, pitch = estimate_head_pose(
                        face_landmarks,
                        width,
                        height
                    )

                    looking_away = (
                        yaw is not None
                        and abs(yaw) > LOOK_AWAY_ANGLE
                    )

                    if looking_away:

                        if look_away_start is None:
                            look_away_start = current_time

                        look_away_duration = (
                            current_time - look_away_start
                        )

                        if look_away_duration >= LOOK_AWAY_SECONDS:

                            look_away_alert_active = True
                            snapshots.setdefault("LOOK_AWAY", raw_frame)

                    else:

                        saved_events.append(finish_event(
                            "LOOK_AWAY",
                            look_away_start,
                            current_time
                        ))

                        look_away_start = None

                else:

                    # Face disappearance ends active face events.

                    saved_events.append(finish_event(
                        "EYES_CLOSED",
                        eyes_closed_start,
                        current_time
                    ))

                    saved_events.append(finish_event(
                        "YAWN",
                        yawn_start,
                        current_time
                    ))

                    saved_events.append(finish_event(
                        "LOOK_AWAY",
                        look_away_start,
                        current_time
                    ))

                    eyes_closed_start = None
                    yawn_start = None
                    look_away_start = None

                # ----------------------------------
                # FATIGUE (PERCLOS) EVENT
                # ----------------------------------

                fatigued = is_fatigued(perclos, fatigue_start is not None)

                if fatigued and fatigue_start is None:

                    fatigue_start = current_time
                    snapshots["FATIGUE"] = raw_frame

                    # One soft chime per crossing, not the siren.
                    play_chime()

                elif not fatigued and fatigue_start is not None:

                    saved_events.append(finish_event(
                        "FATIGUE",
                        fatigue_start,
                        current_time
                    ))

                    fatigue_start = None

                # ----------------------------------
                # YOLO PHONE DETECTION
                # ----------------------------------

                frame_count += 1

                if frame_count % YOLO_FRAME_INTERVAL == 0:

                    phone_detected = False
                    phone_box_to_draw = None

                    try:

                        yolo_results = yolo_model(
                            frame,
                            verbose=False
                        )

                        for result in yolo_results:

                            if result.boxes is None:
                                continue

                            for box in result.boxes:

                                class_id = int(
                                    box.cls[0].item()
                                )

                                if class_id != PHONE_CLASS_ID:
                                    continue

                                confidence = float(
                                    box.conf[0].item()
                                )

                                if confidence < PHONE_CONFIDENCE:
                                    continue

                                coordinates = (
                                    box.xyxy[0]
                                    .cpu()
                                    .numpy()
                                    .astype(int)
                                )

                                px1, py1, px2, py2 = coordinates

                                phone_box = (
                                    px1,
                                    py1,
                                    px2,
                                    py2
                                )

                                phone_box_to_draw = phone_box

                                if (
                                    face_detected
                                    and face_box is not None
                                    and phone_near_face(
                                        phone_box,
                                        face_box
                                    )
                                ):

                                    phone_detected = True
                                    break

                            if phone_detected:
                                break

                    except Exception as error:

                        print(f"YOLO detection error: {error}")

                # ----------------------------------
                # PHONE EVENT TIMING
                # ----------------------------------

                if phone_detected and face_detected:

                    if phone_start is None:
                        phone_start = current_time

                    phone_duration = (
                        current_time - phone_start
                    )

                    if phone_duration >= PHONE_SECONDS:

                        phone_alert_active = True
                        snapshots.setdefault("PHONE", raw_frame)

                else:

                    saved_events.append(finish_event(
                        "PHONE",
                        phone_start,
                        current_time
                    ))

                    phone_start = None

                # ----------------------------------
                # CONTINUOUS ALARM CONTROL
                # ----------------------------------

                alarm_required = (
                    eyes_alert_active
                    or look_away_alert_active
                    or phone_alert_active
                )

                # The reason picks what the alarm says out loud.
                if eyes_alert_active:
                    set_alarm("EYES_CLOSED")
                elif phone_alert_active:
                    set_alarm("PHONE")
                elif look_away_alert_active:
                    set_alarm("LOOK_AWAY")
                else:
                    set_alarm(None)

                # ----------------------------------
                # DRAW HUD
                # ----------------------------------

                for saved in saved_events:
                    if saved is not None:
                        toast = saved
                        toast_time = current_time

                if not face_detected:
                    status = "NO FACE"
                elif alarm_required:
                    status = "ALERT"
                elif yawning or eyes_closed:
                    status = "DROWSY"
                else:
                    status = "ATTENTIVE"

                # Countdown rings, only while a timer runs.
                timers = {}

                if eyes_closed_start is not None:
                    timers["Eyes closed"] = (
                        current_time - eyes_closed_start,
                        EYES_CLOSED_SECONDS
                    )

                if look_away_start is not None:
                    timers["Looking away"] = (
                        current_time - look_away_start,
                        LOOK_AWAY_SECONDS
                    )

                if phone_start is not None:
                    timers["Phone"] = (
                        current_time - phone_start,
                        PHONE_SECONDS
                    )

                hud_state = {
                    "status": status,
                    "driver_id": DRIVER_ID,
                    "timers": timers,
                    "ear": average_ear,
                    "ear_limit": ear_limit,
                    "limit_note": limit_note,
                    "mar": mar,
                    "mar_limit": MAR_THRESHOLD,
                    "yaw": yaw,
                    "yaw_limit": LOOK_AWAY_ANGLE,
                    "alarm": alarm_required,
                    "face_box": face_box,
                    "phone_box": phone_box_to_draw,
                    "perclos": perclos,
                    "take_break": fatigue_start is not None,
                    "toast": toast if current_time - toast_time < 3 else None,
                }

                draw_hud(frame, hud_state)

                # ----------------------------------
                # SHOW CAMERA
                # ----------------------------------

                cv2.imshow(
                    WINDOW_NAME,
                    frame
                )

                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

                if key == ord("c"):

                    # New driver: save what is still open, then calibrate.
                    finish_event("EYES_CLOSED", eyes_closed_start, current_time)
                    finish_event("YAWN", yawn_start, current_time)
                    finish_event("LOOK_AWAY", look_away_start, current_time)
                    finish_event("PHONE", phone_start, current_time)
                    finish_event("FATIGUE", fatigue_start, current_time)

                    eyes_closed_start = None
                    yawn_start = None
                    look_away_start = None
                    phone_start = None
                    fatigue_start = None

                    # PERCLOS belongs to one driver, so start it again.
                    perclos_history.clear()
                    perclos = None

                    calibrating = True
                    calibration_start = None

    except KeyboardInterrupt:

        print("\nDetector stopped by user.")

    finally:

        # Save any event that was still active when
        # the detector stopped.

        shutdown_time = time.monotonic()

        finish_event(
            "EYES_CLOSED",
            eyes_closed_start,
            shutdown_time
        )

        finish_event(
            "YAWN",
            yawn_start,
            shutdown_time
        )

        finish_event(
            "LOOK_AWAY",
            look_away_start,
            shutdown_time
        )

        finish_event(
            "PHONE",
            phone_start,
            shutdown_time
        )

        finish_event(
            "FATIGUE",
            fatigue_start,
            shutdown_time
        )

        alarm_active.clear()

        cap.release()
        cv2.destroyAllWindows()

        stop_alarm_worker(alarm_thread)

        if os.path.exists(ALARM_SOUND):
            os.remove(ALARM_SOUND)

        print("Fleet Safety Detector stopped.")


# ==========================================
# 5. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":
    run_detector()
