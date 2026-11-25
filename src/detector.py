
import cv2
import mediapipe as mp
import os
import time

from pathlib import Path
from ultralytics import YOLO

from db import save_event
from severity import classify_severity
from detection.face_checks import (
    get_landmark_points,
    eye_aspect_ratio,
    calculate_mar,
    estimate_head_pose,
)
from detection.alarm import (
    ALARM_SOUND,
    alarm_active,
    create_alarm_sound,
    start_alarm_worker,
    stop_alarm_worker,
)
from detection.phone_check import get_face_box, phone_near_face


# ==========================================
# 1. SETTINGS
# ==========================================

CAMERA_INDEX = 0

DRIVER_ID = "DRIVER_001"
VEHICLE_ID = "VEHICLE_001"

# Eye detection
EAR_THRESHOLD = 0.20
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


# ==========================================
# 2. EVENT LOGGING
# ==========================================

def log_event(event_type, duration):
    """
    Classify and save an event using its full duration.
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

        return

    try:

        save_event(
            DRIVER_ID,
            VEHICLE_ID,
            event_type,
            round(duration, 2),
            severity
        )

        print(
            f"EVENT SAVED: {event_type} | "
            f"{duration:.2f} seconds | "
            f"Severity: {severity}"
        )

    except Exception as error:

        print(
            f"Database error while saving {event_type}: {error}"
        )


def finish_event(event_type, start_time, end_time):
    """
    Finalize an event when the detected behavior ends.

    Events shorter than their minimum duration are ignored.
    """

    if start_time is None:
        return

    duration = end_time - start_time

    if classify_severity(event_type, duration) != "UNKNOWN":
        log_event(event_type, duration)


# ==========================================
# 3. DISPLAY HELPERS
# ==========================================

def draw_text(
    frame,
    text,
    position,
    color=(255, 255, 255),
    scale=0.65
):

    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2
    )


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
    print("Press Q to quit.")

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

    # YOLO frame tracking.
    frame_count = 0
    phone_detected = False
    phone_box_to_draw = None

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

                height, width, _ = frame.shape
                current_time = time.monotonic()

                # Reset alert states every frame.
                eyes_alert_active = False
                look_away_alert_active = False
                phone_alert_active = False

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

                    fx1, fy1, fx2, fy2 = face_box

                    cv2.rectangle(
                        frame,
                        (fx1, fy1),
                        (fx2, fy2),
                        (255, 255, 0),
                        2
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

                    eyes_closed = average_ear < EAR_THRESHOLD

                    if eyes_closed:

                        if eyes_closed_start is None:
                            eyes_closed_start = current_time

                        closed_duration = (
                            current_time - eyes_closed_start
                        )

                        if closed_duration >= EYES_CLOSED_SECONDS:

                            eyes_alert_active = True

                    else:

                        finish_event(
                            "EYES_CLOSED",
                            eyes_closed_start,
                            current_time
                        )

                        eyes_closed_start = None

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

                    else:

                        finish_event(
                            "YAWN",
                            yawn_start,
                            current_time
                        )

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

                    else:

                        finish_event(
                            "LOOK_AWAY",
                            look_away_start,
                            current_time
                        )

                        look_away_start = None

                    # ----------------------------------
                    # DISPLAY FACE READINGS
                    # ----------------------------------

                    draw_text(
                        frame,
                        f"Left EAR: {left_ear:.3f}",
                        (20, 30)
                    )

                    draw_text(
                        frame,
                        f"Right EAR: {right_ear:.3f}",
                        (20, 60)
                    )

                    draw_text(
                        frame,
                        f"Average EAR: {average_ear:.3f}",
                        (20, 90)
                    )

                    draw_text(
                        frame,
                        f"MAR: {mar:.3f}",
                        (20, 120)
                    )

                    if yaw is not None:

                        draw_text(
                            frame,
                            f"Head yaw: {yaw:.1f}",
                            (20, 150)
                        )

                    if eyes_closed:

                        draw_text(
                            frame,
                            "WARNING: EYES CLOSED",
                            (20, 195),
                            (0, 0, 255),
                            0.8
                        )

                    if yawning:

                        draw_text(
                            frame,
                            "YAWNING",
                            (20, 225),
                            (0, 165, 255)
                        )

                    if looking_away:

                        draw_text(
                            frame,
                            "LOOKING AWAY",
                            (20, 255),
                            (0, 0, 255)
                        )

                else:

                    # Face disappearance ends active face events.

                    finish_event(
                        "EYES_CLOSED",
                        eyes_closed_start,
                        current_time
                    )

                    finish_event(
                        "YAWN",
                        yawn_start,
                        current_time
                    )

                    finish_event(
                        "LOOK_AWAY",
                        look_away_start,
                        current_time
                    )

                    eyes_closed_start = None
                    yawn_start = None
                    look_away_start = None

                    draw_text(
                        frame,
                        "NO FACE DETECTED",
                        (20, 50),
                        (0, 0, 255),
                        0.9
                    )

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

                else:

                    finish_event(
                        "PHONE",
                        phone_start,
                        current_time
                    )

                    phone_start = None

                # ----------------------------------
                # CONTINUOUS ALARM CONTROL
                # ----------------------------------

                alarm_required = (
                    eyes_alert_active
                    or look_away_alert_active
                    or phone_alert_active
                )

                if alarm_required:

                    alarm_active.set()

                    draw_text(
                        frame,
                        "!!! EMERGENCY ALERT - PAY ATTENTION !!!",
                        (20, 335),
                        (0, 0, 255),
                        0.8
                    )

                    draw_text(
                        frame,
                        "ALARM ACTIVE - CORRECT YOUR BEHAVIOR",
                        (20, 370),
                        (0, 0, 255),
                        0.65
                    )

                else:

                    alarm_active.clear()

                # ----------------------------------
                # DRAW PHONE BOX
                # ----------------------------------

                if phone_box_to_draw is not None:

                    px1, py1, px2, py2 = phone_box_to_draw

                    cv2.rectangle(
                        frame,
                        (px1, py1),
                        (px2, py2),
                        (0, 165, 255),
                        2
                    )

                    draw_text(
                        frame,
                        "PHONE",
                        (px1, max(20, py1 - 10)),
                        (0, 165, 255)
                    )

                if phone_detected:

                    draw_text(
                        frame,
                        "PHONE NEAR FACE",
                        (20, 290),
                        (0, 0, 255),
                        0.8
                    )

                # ----------------------------------
                # SHOW CAMERA
                # ----------------------------------

                cv2.imshow(
                    WINDOW_NAME,
                    frame
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

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
