# Checks the PERCLOS maths. Run from the project folder: python tests/test_perclos.py

import sys
from collections import deque

sys.path.insert(0, "src")
from detection.face_checks import update_perclos, is_fatigued


def feed(history, start, seconds, closed, fps=10):
    """Add `seconds` of frames; return the last PERCLOS value."""

    value = None
    for i in range(int(seconds * fps)):
        value = update_perclos(history, start + i / fps, closed)
    return value


# "Warming up" under 30 s of data.
history = deque()
assert feed(history, 0, 29, False) is None

# Known mix: 54 s open + 6 s closed = 10 % closed.
history = deque()
feed(history, 0, 54, False)
value = feed(history, 54, 6, True)
assert abs(value - 0.10) < 0.01, value

# Old entries dropped: after 60 more seconds of open eyes, the closed frames are gone.
value = feed(history, 60, 60, False)
assert value == 0.0, value
assert all(now >= 59 for now, _ in history)
assert len(history) <= 601

# Event start/stop with the 15 % / 12 % gap.
assert is_fatigued(0.16, False) is True     # crosses 15 % -> starts
assert is_fatigued(0.14, True) is True      # between: stays on
assert is_fatigued(0.14, False) is False    # between: stays off
assert is_fatigued(0.11, True) is False     # below 12 % -> ends
assert is_fatigued(None, False) is False    # warming up: no change
assert is_fatigued(None, True) is True

# Full run: 20 % closed starts it, then open eyes bring it below 12 %.
history = deque()
fatigued = False
starts = ends = 0
for i in range(1800):                       # 180 s at 10 fps
    now = i / 10
    closed = now < 60 and i % 5 == 0        # 20 % closed for the first minute
    was = fatigued
    fatigued = is_fatigued(update_perclos(history, now, closed), fatigued)
    starts += fatigued and not was
    ends += was and not fatigued
assert (starts, ends) == (1, 1), (starts, ends)
assert fatigued is False

print("PERCLOS tests passed!")
