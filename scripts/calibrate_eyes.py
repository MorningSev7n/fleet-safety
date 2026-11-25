
import cv2
import mediapipe as mp
import math
import sys


# ==========================================
# 1. SETTINGS
# ==========================================

EAR_THRESHOLD = 0.20  # Temporary threshold; calibrate using webcam readings

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]


# ==========================================
# 2. EAR CALCULATION
# ==========================================

def calculate_distance(point1, point2):
    return math.dist(point1, point2)


def eye_aspect_ratio(eye):
    """
    Calculate EAR using six eye landmarks.
    Lower EAR means the eye is more closed.
    """

    p1, p2, p3, p4, p5, p6 = eye

    horizontal = calculate_distance(p1, p4)

    if horizontal == 0:
        return 0.0

    vertical_1 = calculate_distance(p2, p6)
    vertical_2 = calculate_distance(p3, p5)

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


# ==========================================
# 3. LANDMARK CONVERSION
# ==========================================

def get_eye_points(face_landmarks, eye_indices, width, height):

    points = []

    for index in eye_indices:
        landmark = face_landmarks.landmark[index]

        x = int(landmark.x * width)
        y = int(landmark.y * height)

        points.append((x, y))

    return points


def draw_eye_points(frame, points):

    for x, y in points:
        cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)


# ==========================================
# 4. EAR SELF-TEST
# ==========================================

def run_self_test():

    # Example of an open eye
    open_eye = [
        (0, 0),
        (1, 1),
        (3, 1),
        (4, 0),
        (3, -1),
        (1, -1)
    ]

    # Example of a closed eye
    closed_eye = [
        (0, 0),
        (1, 0),
        (3, 0),
        (4, 0),
        (3, 0),
        (1, 0)
    ]

    open_ear = eye_aspect_ratio(open_eye)
    closed_ear = eye_aspect_ratio(closed_eye)

    assert abs(open_ear - 0.5) < 0.000001
    assert closed_ear == 0.0

    print("EAR self-test passed!")
    print(f"Open example EAR: {open_ear:.3f}")
    print(f"Closed example EAR: {closed_ear:.3f}")


# ==========================================
# 5. WEBCAM TEST
# ==========================================

def run_webcam_test():

    mp_face_mesh = mp.solutions.face_mesh

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        return

    print("Fleet Safety - Eye Testing")
    print("Look at the camera and test your eyes.")
    print("Press Q to quit.")

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

                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                results = face_mesh.process(rgb_frame)

                if results.multi_face_landmarks:

                    face_landmarks = results.multi_face_landmarks[0]

                    # Get both eyes
                    left_points = get_eye_points(
                        face_landmarks,
                        LEFT_EYE,
                        width,
                        height
                    )

                    right_points = get_eye_points(
                        face_landmarks,
                        RIGHT_EYE,
                        width,
                        height
                    )

                    # Calculate EAR
                    left_ear = eye_aspect_ratio(left_points)
                    right_ear = eye_aspect_ratio(right_points)

                    average_ear = (left_ear + right_ear) / 2.0

                    # Draw eye landmarks
                    draw_eye_points(frame, left_points)
                    draw_eye_points(frame, right_points)

                    # Determine temporary eye status
                    if average_ear < EAR_THRESHOLD:
                        eye_status = "CLOSED"
                        color = (0, 0, 255)
                    else:
                        eye_status = "OPEN"
                        color = (0, 255, 0)

                    # Display readings
                    cv2.putText(
                        frame,
                        f"Left EAR: {left_ear:.3f}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Right EAR: {right_ear:.3f}",
                        (20, 75),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Average EAR: {average_ear:.3f}",
                        (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Eyes: {eye_status}",
                        (20, 160),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        color,
                        3
                    )

                    cv2.putText(
                        frame,
                        f"Temporary threshold: {EAR_THRESHOLD}",
                        (20, 200),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

                else:

                    cv2.putText(
                        frame,
                        "NO FACE DETECTED",
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (0, 0, 255),
                        2
                    )

                cv2.imshow(
                    "Fleet Safety - Eye Testing",
                    frame
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:

        cap.release()
        cv2.destroyAllWindows()

        print("Eye testing finished.")


# ==========================================
# 6. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    if "--self-test" in sys.argv:
        run_self_test()
    else:
        run_webcam_test()
