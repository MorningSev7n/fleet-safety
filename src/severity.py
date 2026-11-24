
# ==========================================
# FLEET SAFETY - SEVERITY CLASSIFICATION
# ==========================================

# Minimum duration, MEDIUM threshold,
# HIGH threshold, and maximum synthetic duration.

SEVERITY_RULES = {
    "EYES_CLOSED": {
        "minimum": 1.5,
        "medium": 2.0,
        "high": 3.0,
        "maximum": 5.0,
    },
    "YAWN": {
        "minimum": 1.0,
        "medium": 1.5,
        "high": 2.5,
        "maximum": 4.0,
    },
    "LOOK_AWAY": {
        "minimum": 2.0,
        "medium": 3.0,
        "high": 4.0,
        "maximum": 6.0,
    },
    "PHONE": {
        "minimum": 1.0,
        "medium": 2.0,
        "high": 4.0,
        "maximum": 8.0,
    },
}


def classify_severity(event_type, duration):
    """
    Determine event severity using its type and duration.

    Returns LOW, MEDIUM, HIGH, or UNKNOWN.
    """

    rules = SEVERITY_RULES.get(event_type)

    if rules is None:
        return "UNKNOWN"

    try:
        duration = float(duration)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if duration < rules["minimum"]:
        return "UNKNOWN"

    if duration >= rules["high"]:
        return "HIGH"

    if duration >= rules["medium"]:
        return "MEDIUM"

    return "LOW"
