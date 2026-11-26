# ==========================================
# FLEET SAFETY - CAMERA HUD
# ==========================================

# Draws the on-screen display for the detector.
# Shapes are drawn with OpenCV (fast), and all text is drawn
# in one Pillow pass at the end (nicer font than cv2.putText).

import math
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


FONT_PATH = "/System/Library/Fonts/SFNS.ttf"

# Colors are BGR, like the rest of OpenCV.
GREEN = (80, 200, 60)
AMBER = (0, 170, 255)
RED = (60, 60, 235)
GREY = (160, 160, 160)
WHITE = (255, 255, 255)
CYAN = (255, 255, 0)
ORANGE = (0, 165, 255)

STATUS_COLORS = {
    "ATTENTIVE": GREEN,
    "DROWSY": AMBER,
    "ALERT": RED,
    "NO FACE": GREY,
}

SEVERITY_COLORS = {
    "LOW": GREEN,
    "MEDIUM": AMBER,
    "HIGH": RED,
}

BAR_HEIGHT = 56

# Load the font sizes once at import, not every frame.
try:
    FONTS = {
        size: ImageFont.truetype(FONT_PATH, size)
        for size in (16, 18, 22, 28)
    }
except OSError:
    FONTS = None
    print("HUD: font not found, using OpenCV text instead.")


# ==========================================
# SMALL HELPERS
# ==========================================

def darken(frame, x1, y1, x2, y2, keep=0.35):
    """Make a see-through dark panel (keeps 35% of the image)."""

    x1, y1 = max(0, x1), max(0, y1)
    region = frame[y1:y2, x1:x2]
    frame[y1:y2, x1:x2] = (region * keep).astype(np.uint8)


def draw_all_text(frame, texts):
    """
    Draw every text item in one go.
    Each item is (x, y, text, size, color, anchor).
    anchor "la" = x,y is top-left, "mm" = x,y is the center.
    """

    if FONTS is None:

        for x, y, text, size, color, anchor in texts:

            scale = size / 32
            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)

            if anchor == "mm":
                x, y = x - w // 2, y + h // 2
            elif anchor == "lm":
                y = y + h // 2
            else:
                y = y + h

            cv2.putText(frame, text, (int(x), int(y)),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
        return

    # The frame stays BGR; Pillow just sees 3 channels, so BGR colors
    # come out right without converting the whole image.
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)

    for x, y, text, size, color, anchor in texts:
        draw.text((x, y), text, font=FONTS[size], fill=color, anchor=anchor)

    frame[:] = np.asarray(image)


def text_width(text, size):

    if FONTS is None:
        return cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, size / 32, 1)[0][0]

    return int(FONTS[size].getlength(text))


# ==========================================
# HUD PARTS
# ==========================================

def draw_top_bar(frame, state, texts):

    width = frame.shape[1]
    darken(frame, 0, 0, width, BAR_HEIGHT)

    status = state.get("status", "ATTENTIVE")
    color = STATUS_COLORS.get(status, WHITE)

    cv2.circle(frame, (28, BAR_HEIGHT // 2), 9, color, -1, cv2.LINE_AA)
    texts.append((48, BAR_HEIGHT // 2 - 15, status, 28, color, "la"))

    right_text = f"{state.get('driver_id', '')}   {time.strftime('%H:%M:%S')}"
    texts.append((width - 20 - text_width(right_text, 22),
                  BAR_HEIGHT // 2 - 12, right_text, 22, WHITE, "la"))


def draw_gauge(frame, texts, x, y, label, value, low, high, limit, bad_below):
    """One horizontal bar with the limit marked as a white tick."""

    bar_w, bar_h = 180, 10
    texts.append((x, y, f"{label}  {value:.2f}", 16, WHITE, "la"))

    top = y + 24
    cv2.rectangle(frame, (x, top), (x + bar_w, top + bar_h), (70, 70, 70), -1)

    share = min(max((value - low) / (high - low), 0.0), 1.0)
    over_limit = value < limit if bad_below else value > limit
    fill_color = AMBER if over_limit else GREEN
    cv2.rectangle(frame, (x, top), (x + int(bar_w * share), top + bar_h), fill_color, -1)

    limit_x = x + int(bar_w * (limit - low) / (high - low))
    cv2.line(frame, (limit_x, top - 4), (limit_x, top + bar_h + 4), WHITE, 2)


def draw_yaw_gauge(frame, texts, x, y, yaw, limit, span=60):
    """Centered bar: dot moves left/right with the head, ticks at +/- limit."""

    bar_w, bar_h = 180, 10
    texts.append((x, y, f"Head  {yaw:+.0f}°", 16, WHITE, "la"))

    top = y + 24
    center = x + bar_w // 2
    cv2.rectangle(frame, (x, top), (x + bar_w, top + bar_h), (70, 70, 70), -1)

    for side in (-1, 1):
        tick_x = center + int(side * bar_w / 2 * limit / span)
        cv2.line(frame, (tick_x, top - 4), (tick_x, top + bar_h + 4), WHITE, 2)

    clipped = min(max(yaw, -span), span)
    dot_x = center + int(bar_w / 2 * clipped / span)
    dot_color = AMBER if abs(yaw) > limit else GREEN
    cv2.circle(frame, (dot_x, top + bar_h // 2), 8, dot_color, -1, cv2.LINE_AA)


def draw_gauges(frame, state, texts):

    if state.get("ear") is None:
        return

    x, y = 20, BAR_HEIGHT + 16
    darken(frame, x - 12, y - 10, x + 192, y + 3 * 52 + 2)

    draw_gauge(frame, texts, x, y, "Eyes", state["ear"],
               0.0, 0.40, state["ear_limit"], bad_below=True)

    draw_gauge(frame, texts, x, y + 52, "Mouth", state["mar"],
               0.0, 1.0, state["mar_limit"], bad_below=False)

    if state.get("yaw") is not None:
        draw_yaw_gauge(frame, texts, x, y + 104, state["yaw"], state["yaw_limit"])


def draw_rings(frame, state, texts):
    """A countdown ring for each running timer, bottom center."""

    timers = state.get("timers", {})

    if not timers:
        return

    height, width = frame.shape[:2]
    radius, gap = 46, 150
    start_x = width // 2 - gap * (len(timers) - 1) // 2
    cy = height - 110

    for i, (name, (elapsed, limit)) in enumerate(timers.items()):

        cx = start_x + i * gap
        share = min(elapsed / limit, 1.0)
        color = RED if share >= 1.0 else AMBER

        darken(frame, cx - 64, cy - 60, cx + 64, cy + 84)
        cv2.circle(frame, (cx, cy), radius, (70, 70, 70), 6, cv2.LINE_AA)
        cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, 360 * share,
                    color, 6, cv2.LINE_AA)

        texts.append((cx, cy, f"{elapsed:.1f} / {limit:.1f} s", 16, WHITE, "mm"))
        texts.append((cx, cy + radius + 20, name, 16, color, "mm"))


def draw_alarm_border(frame):
    """Red border that pulses while the alarm is on."""

    pulse = (math.sin(time.monotonic() * 6) + 1) / 2
    thickness = int(6 + 10 * pulse)
    color = (0, 0, int(150 + 105 * pulse))
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width - 1, height - 1), color, thickness)


def draw_toast(frame, state, texts):
    """Card in the bottom-right after an event was saved."""

    toast = state.get("toast")

    if toast is None:
        return

    event_type, duration, severity = toast
    text = f"Logged: {event_type} · {duration:.1f} s · {severity}"

    height, width = frame.shape[:2]
    card_w = text_width(text, 18) + 40
    x2, y2 = width - 24, height - 24
    x1, y1 = x2 - card_w, y2 - 48

    darken(frame, x1, y1, x2, y2, keep=0.2)
    cv2.rectangle(frame, (x1, y1), (x1 + 6, y2), SEVERITY_COLORS.get(severity, WHITE), -1)
    texts.append((x1 + 22, y1 + 24, text, 18, WHITE, "lm"))


def draw_face_brackets(frame, face_box):
    """Thin corner brackets instead of a full box."""

    x1, y1, x2, y2 = face_box
    length = max(12, (x2 - x1) // 5)

    for cx, cy, dx, dy in (
        (x1, y1, 1, 1), (x2, y1, -1, 1),
        (x1, y2, 1, -1), (x2, y2, -1, -1),
    ):
        cv2.line(frame, (cx, cy), (cx + dx * length, cy), CYAN, 2, cv2.LINE_AA)
        cv2.line(frame, (cx, cy), (cx, cy + dy * length), CYAN, 2, cv2.LINE_AA)


def draw_phone_box(frame, phone_box, texts):

    x1, y1, x2, y2 = phone_box
    cv2.rectangle(frame, (x1, y1), (x2, y2), ORANGE, 2)
    texts.append((x1, max(BAR_HEIGHT + 4, y1 - 24), "PHONE", 18, ORANGE, "la"))


# ==========================================
# ENTRY POINT
# ==========================================

def draw_hud(frame, state):
    """
    Draw the whole HUD on the frame (in place).

    state keys: status, driver_id, timers {name: (elapsed, limit)},
    ear/ear_limit, mar/mar_limit, yaw/yaw_limit (None when no face),
    alarm (bool), face_box, phone_box, toast (event_type, duration, severity).
    """

    texts = []

    if state.get("face_box") is not None:
        draw_face_brackets(frame, state["face_box"])

    if state.get("phone_box") is not None:
        draw_phone_box(frame, state["phone_box"], texts)

    draw_top_bar(frame, state, texts)
    draw_gauges(frame, state, texts)
    draw_rings(frame, state, texts)
    draw_toast(frame, state, texts)

    if state.get("alarm"):
        draw_alarm_border(frame)

    draw_all_text(frame, texts)
