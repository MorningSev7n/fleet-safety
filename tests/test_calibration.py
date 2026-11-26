# Checks calibrate_threshold. Run from the project folder: python tests/test_calibration.py

import sys

sys.path.insert(0, "src")
from detection.face_checks import calibrate_threshold


# Median x 0.75.
assert abs(calibrate_threshold([0.28] * 40) - 0.21) < 1e-9
assert abs(calibrate_threshold([0.26, 0.28, 0.30] * 20) - 0.21) < 1e-9

# A few blinks in 5 s barely move it.
with_blinks = [0.28] * 140 + [0.05] * 10
assert abs(calibrate_threshold(with_blinks) - 0.21) < 1e-9

# Too few samples (face not found most of the time).
assert calibrate_threshold([0.28] * 29) is None
assert calibrate_threshold([]) is None

# Squinting or not looking at the camera.
assert calibrate_threshold([0.12] * 60) is None

print("Calibration tests passed!")
