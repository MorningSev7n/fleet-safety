
import cv2
import mediapipe as mp
import numpy as np
import math
import os
import subprocess
import threading
import time
import wave
import struct
import tempfile

from ultralytics import YOLO
from db import save_event
from pathlib import Path


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

MOUTH_VERTICAL = [13, 14, 82, 87, 312, 317]
MOUTH_HORIZONTAL = [78, 308]

# Looking-away detection
LOOK_AWAY_ANGLE = 25
LOOK_AWAY_SECONDS = 2.0

# Phone detection
ROOT = Path(__file__).resolve().parent.parent
YOLO_MODEL = str(ROOT / "models" / "yolo26n.pt")
YOLO_FRAME_INTERVAL = 5
PHONE_SECONDS = 1.0
PHONE_CLASS_ID = 67

# Alarm
ALARM_FREQUENCY_LOW = 650
ALARM_FREQUENCY_HIGH = 1100
ALARM_DURATION = 1.2
ALARM_VOLUME = 0.65

# Display
WINDOW_NAME = "Fleet Safety - Driver Monitoring"


# ==========================================
# 2. FACE LANDMARK HELPERS
# ==========================================

def calculate_distance(point1, point2):
    return math.dist(point1, point2)


def get_landmark_points(face_landmarks, indices, width, height):
    """Convert selected face landmarks into pixel coordinates."""

    points = []

    for index in indices:
        landmark = face_landmarks.landmark[index]

        x = int(landmark.x * width)
        y = int(landmark.y * height)

        points.append((x, y))

    return points


def eye_aspect_ratio(eye):
    """Calculate EAR using six eye landmarks."""

    p1, p2, p3, p4, p5, p6 = eye

    horizontal = calculate_distance(p1, p4)

    if horizontal == 0:
        return 0.0

    vertical_1 = calculate_distance(p2, p6)
    vertical_2 = calculate_distance(p3, p5)

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def calculate_mar(face_landmarks, width, height):
    """Calculate mouth aspect ratio using Face Mesh landmarks."""

    vertical_points = get_landmark_points(
        face_landmarks,
        MOUTH_VERTICAL,
        width,
        height
    )

    horizontal_points = get_landmark_points(
        face_landmarks,
        MOUTH_HORIZONTAL,
        width,
        height
    )

    vertical_1 = calculate_distance(
        vertical_points[0],
        vertical_points[1]
    )

    vertical_2 = calculate_distance(
        vertical_points[2],
        vertical_points[3]
    )

    vertical_3 = calculate_distance(
        vertical_points[4],
        vertical_points[5]
    )

    horizontal = calculate_distance(
        horizontal_points[0],
        horizontal_points[1]
    )

    if horizontal == 0:
        return 0.0

    return (
        vertical_1 + vertical_2 + vertical_3
    ) / (3.0 * horizontal)


# ==========================================
# 3. HEAD POSE ESTIMATION
# ==========================================

FACE_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (225.0, 170.0, -135.0),
    (-225.0, 170.0, -135.0),
    (150.0, -150.0, -125.0),
    (-150.0, -150.0, -125.0)
], dtype=np.float64)

POSE_LANDMARKS = [1, 152, 263, 33, 291, 61]


def estimate_head_pose(face_landmarks, width, height):
    """
    Estimate head yaw and pitch using OpenCV solvePnP.
    Angles are approximate and should be calibrated.
    """

    image_points = get_landmark_points(
        face_landmarks,
        POSE_LANDMARKS,
        width,
        height
    )

    image_points = np.array(
        image_points,
        dtype=np.float64
    )

    focal_length = width

    camera_matrix = np.array([
        [focal_length, 0, width / 2],
        [0, focal_length, height / 2],
        [0, 0, 1]
    ], dtype=np.float64)

    distortion = np.zeros((4, 1))

    success, rotation_vector, translation_vector = cv2.solvePnP(
        FACE_MODEL_POINTS,
        image_points,
        camera_matrix,
        distortion,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None, None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

    sy = math.sqrt(
        rotation_matrix[0, 0] ** 2
        + rotation_matrix[1, 0] ** 2
    )

    singular = sy < 1e-6

    if not singular:
        pitch = math.atan2(
            rotation_matrix[2, 1],
            rotation_matrix[2, 2]
        )

        yaw = math.atan2(
            -rotation_matrix[2, 0],
            sy
        )

    else:
        pitch = math.atan2(
            -rotation_matrix[1, 2],
            rotation_matrix[1, 1]
        )

        yaw = math.atan2(
            -rotation_matrix[2, 0],
            sy
        )

    return math.degrees(yaw), math.degrees(pitch)


# ==========================================
# 4. CONTINUOUS ALARM
# ==========================================

ALARM_SOUND = os.path.join(
    tempfile.gettempdir(),
    "fleet_safety_alarm.wav"
)

alarm_active = threading.Event()
alarm_shutdown = threading.Event()


def create_alarm_sound():
    """
    Generate a repeating two-tone siren using Python's
    built-in wave library. No extra audio package needed.
    """

    sample_rate = 44100
    total_samples = int(sample_rate * ALARM_DURATION)

    with wave.open(ALARM_SOUND, "wb") as sound_file:

        sound_file.setnchannels(1)
        sound_file.setsampwidth(2)
        sound_file.setframerate(sample_rate)

        audio_data = []

        for i in range(total_samples):

            progress = i / total_samples

            # Sweep between low and high frequencies
            frequency = (
                ALARM_FREQUENCY_LOW
                + (ALARM_FREQUENCY_HIGH - ALARM_FREQUENCY_LOW)
                * (0.5 - 0.5 * math.cos(2 * math.pi * progress))
            )

            current_time = i / sample_rate

            # Short pauses create an urgent warning pattern
            pulse_position = current_time % 0.4

            if pulse_position < 0.28:
                amplitude = ALARM_VOLUME
            else:
                amplitude = 0.0

            sample = int(
                32767
                * amplitude
                * math.sin(2 * math.pi * frequency * current_time)
            )

            audio_data.append(
                struct.pack("<h", sample)
            )

        sound_file.writeframes(b"".join(audio_data))

    print("Emergency alarm sound generated.")


def play_alarm_continuously():
    """
    Keep playing the alarm while unsafe behavior is detected.

    The sound stops when alarm_active is cleared.
    """

    while not alarm_shutdown.is_set():

        if not alarm_active.wait(timeout=0.1):
            continue

        while alarm_active.is_set() and not alarm_shutdown.is_set():

            try:

                if not os.path.exists(ALARM_SOUND):
                    print("ERROR: Alarm sound file is missing.")
                    alarm_active.wait(timeout=0.5)
                    continue

                process = subprocess.Popen(
                    ["afplay", ALARM_SOUND],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Monitor playback so it can stop immediately
                while (
                    process.poll() is None
                    and alarm_active.is_set()
                    and not alarm_shutdown.is_set()
                ):
                    time.sleep(0.05)

                # Stop the current sound if the driver recovers
                if process.poll() is None:

                    process.terminate()

                    try:
                        process.wait(timeout=0.5)

                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

            except Exception as error:

                print(f"Alarm playback error: {error}")
                alarm_active.wait(timeout=0.5)

    print("Alarm thread stopped.")


def start_alarm_worker():
    """Start one background thread for the alarm."""

    thread = threading.Thread(
        target=play_alarm_continuously,
        daemon=True
    )

    thread.start()

    return thread


def stop_alarm_worker(thread):
    """Stop the alarm and shut down its background thread."""

    alarm_active.clear()
    alarm_shutdown.set()

    if thread is not None:
        thread.join(timeout=2.0)


# ==========================================
# 5. EVENT LOGGING
# ==========================================

def log_event(event_type, duration):
    """Save an event using the existing database function."""

    severity = "HIGH"

    try:

        save_event(
            DRIVER_ID,
            VEHICLE_ID,
            event_type,
            round(duration, 2),
            severity
        )

        print(
            f"EVENT SAVED: {event_type} "
            f"({duration:.2f} seconds)"
        )

    except Exception as error:

        print(
            f"Database error while saving {event_type}: {error}"
        )


# ==========================================
# 6. DISPLAY HELPERS
# ==========================================

def draw_text(frame, text, position, color=(255, 255, 255), scale=0.65):

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
# 7. PHONE DETECTION HELPERS
# ==========================================

def get_face_box(face_landmarks, width, height):
    """Return a bounding box around the detected face."""

    xs = [
        int(point.x * width)
        for point in face_landmarks.landmark
    ]

    ys = [
        int(point.y * height)
        for point in face_landmarks.landmark
    ]

    return (
        max(0, min(xs)),
        max(0, min(ys)),
        min(width, max(xs)),
        min(height, max(ys))
    )


def phone_near_face(phone_box, face_box):
    """Check whether a phone overlaps an expanded face box."""

    px1, py1, px2, py2 = phone_box
    fx1, fy1, fx2, fy2 = face_box

    face_width = fx2 - fx1
    face_height = fy2 - fy1

    margin_x = int(face_width * 0.5)
    margin_y = int(face_height * 0.5)

    expanded_face = (
        max(0, fx1 - margin_x),
        max(0, fy1 - margin_y),
        fx2 + margin_x,
        fy2 + margin_y
    )

    ex1, ey1, ex2, ey2 = expanded_face

    return (
        px1 < ex2
        and px2 > ex1
        and py1 < ey2
        and py2 > ey1
    )


# ==========================================
# 8. MAIN DETECTOR
# ==========================================

def run_detector():

    print("Starting Fleet Safety Driver Monitoring...")
    print("Press Q to quit.")

    # Generate the emergency siren
    try:
        create_alarm_sound()

    except Exception as error:
        print(f"Could not generate alarm sound: {error}")
        return

    # Start the alarm background thread
    alarm_thread = start_alarm_worker()

    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():

        print("ERROR: Could not open webcam.")
        stop_alarm_worker(alarm_thread)
        return

    # Load YOLO
    try:

        print(f"Loading YOLO model: {YOLO_MODEL}")
        yolo_model = YOLO(YOLO_MODEL)

    except Exception as error:

        print(f"ERROR: Could not load YOLO model: {error}")

        cap.release()
        stop_alarm_worker(alarm_thread)

        return

    mp_face_mesh = mp.solutions.face_mesh

    # Event timing
    eyes_closed_start = None
    eyes_event_logged = False

    yawn_start = None
    yawn_event_logged = False

    look_away_start = None
    look_away_event_logged = False

    phone_start = None
    phone_event_logged = False

    # YOLO frame tracking
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

                # Reset alert states every frame
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

                            if not eyes_event_logged:

                                log_event(
                                    "EYES_CLOSED",
                                    closed_duration
                                )

                                eyes_event_logged = True

                    else:

                        eyes_closed_start = None
                        eyes_event_logged = False

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

                        yawn_duration = current_time - yawn_start

                        if (
                            yawn_duration >= YAWN_SECONDS
                            and not yawn_event_logged
                        ):

                            log_event("YAWN", yawn_duration)
                            yawn_event_logged = True

                    else:

                        yawn_start = None
                        yawn_event_logged = False

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

                            if not look_away_event_logged:

                                log_event(
                                    "LOOK_AWAY",
                                    look_away_duration
                                )

                                look_away_event_logged = True

                    else:

                        look_away_start = None
                        look_away_event_logged = False

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

                    # Reset face-dependent event timers
                    eyes_closed_start = None
                    eyes_event_logged = False

                    yawn_start = None
                    yawn_event_logged = False

                    look_away_start = None
                    look_away_event_logged = False

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

                                if confidence < 0.35:
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

                    phone_duration = current_time - phone_start

                    if phone_duration >= PHONE_SECONDS:

                        phone_alert_active = True

                        if not phone_event_logged:

                            log_event("PHONE", phone_duration)
                            phone_event_logged = True

                else:

                    phone_start = None
                    phone_event_logged = False

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

        alarm_active.clear()

        cap.release()
        cv2.destroyAllWindows()

        stop_alarm_worker(alarm_thread)

        # Remove the temporary alarm file
        if os.path.exists(ALARM_SOUND):
            os.remove(ALARM_SOUND)

        print("Fleet Safety Detector stopped.")


# ==========================================
# 9. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":
    run_detector()
