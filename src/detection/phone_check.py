"""Helpers for checking whether a YOLO phone box is near the face. Moved from detector.py unchanged."""


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

