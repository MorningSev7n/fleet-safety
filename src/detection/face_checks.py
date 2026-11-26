"""Face landmark maths: EAR (eyes), MAR (mouth) and head pose. Moved from detector.py unchanged."""

import cv2
import numpy as np
import math
import statistics


MOUTH_VERTICAL = [13, 14, 82, 87, 312, 317]
MOUTH_HORIZONTAL = [78, 308]


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
    """Estimate head yaw and pitch using OpenCV solvePnP."""

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
# 4. PER-DRIVER EYE CALIBRATION
# ==========================================

def calibrate_threshold(ear_samples):
    """
    Turn a few seconds of open-eye EAR readings into this driver's limit.
    Median ignores blinks; 75% of it still counts half-closed eyes as closed.
    Returns None when the samples can't be trusted.
    """

    if len(ear_samples) < 30:
        return None

    baseline = statistics.median(ear_samples)

    # Below 0.15 the driver was squinting or not looking at the camera.
    if baseline < 0.15:
        return None

    return baseline * 0.75
