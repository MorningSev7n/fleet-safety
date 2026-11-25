
from datetime import datetime, timedelta
import random


DRIVERS = [
    "DRIVER_001",
    "DRIVER_002",
    "DRIVER_003",
    "DRIVER_004",
    "DRIVER_005",
]

VEHICLES = [
    "VEHICLE_001",
    "VEHICLE_002",
    "VEHICLE_003",
    "VEHICLE_004",
    "VEHICLE_005",
]


# Synthetic project thresholds
BRAKING_THRESHOLD = 3.5
CORNERING_THRESHOLD = 4.5
SPEEDING_THRESHOLD_PERCENT = 10


def get_braking_severity(value):
    """Classify braking severity using deceleration in m/s²."""

    if value >= 5.5:
        return "HIGH"
    elif value >= 4.5:
        return "MEDIUM"
    else:
        return "LOW"


def get_cornering_severity(value):
    """Classify cornering severity using lateral acceleration in m/s²."""

    if value >= 5.5:
        return "HIGH"
    elif value >= 5.0:
        return "MEDIUM"
    else:
        return "LOW"


def get_speeding_severity(speed, speed_limit):
    """Classify speeding severity using percentage above the speed limit."""

    percentage_over = (
        (speed - speed_limit) / speed_limit
    ) * 100

    if percentage_over >= 30:
        return "HIGH"
    elif percentage_over >= 20:
        return "MEDIUM"
    else:
        return "LOW"


def generate_driving_events():
    """Generate exactly 40 synthetic driving behaviour events."""

    event_specs = []

    # 14 harsh braking events
    braking_values = [
        3.8, 4.0, 4.2, 4.4, 3.9,
        4.6, 4.8, 5.0, 5.2, 4.7,
        5.6, 5.9, 6.1, 5.7,
    ]

    for value in braking_values:
        event_specs.append({
            "event_type": "HARSH_BRAKING",
            "measured_value": value,
            "threshold_value": BRAKING_THRESHOLD,
            "severity": get_braking_severity(value),
        })

    # 13 harsh cornering events
    cornering_values = [
        4.6, 4.7, 4.8, 4.9,
        5.0, 5.1, 5.2, 5.3, 5.0,
        5.5, 5.7, 5.9, 5.6,
    ]

    for value in cornering_values:
        event_specs.append({
            "event_type": "HARSH_CORNERING",
            "measured_value": value,
            "threshold_value": CORNERING_THRESHOLD,
            "severity": get_cornering_severity(value),
        })

    # 13 speeding events
    speeding_specs = [
        (56, 50),
        (58, 50),
        (59, 50),
        (57, 50),
        (72, 60),
        (74, 60),
        (75, 60),
        (76, 60),
        (77, 60),
        (79, 60),
        (91, 60),
        (95, 60),
        (98, 60),
    ]

    for speed, speed_limit in speeding_specs:
        threshold = speed_limit * (
            1 + SPEEDING_THRESHOLD_PERCENT / 100
        )

        event_specs.append({
            "event_type": "SPEEDING",
            "measured_value": speed,
            "threshold_value": round(threshold, 2),
            "severity": get_speeding_severity(
                speed,
                speed_limit,
            ),
        })

    # Shuffle the event types so each driver gets a varied sample.
    random.Random(42).shuffle(event_specs)

    events = []
    now = datetime.now()

    for index, spec in enumerate(event_specs):

        driver_index = index % len(DRIVERS)

        # Spread events across the previous 14 days.
        event_time = now - timedelta(
            days=index % 14,
            hours=(index * 3) % 24,
        )

        event = {
            "timestamp": event_time.isoformat(timespec="seconds"),
            "driver_id": DRIVERS[driver_index],
            "vehicle_id": VEHICLES[driver_index],
            "event_type": spec["event_type"],
            "measured_value": spec["measured_value"],
            "threshold_value": spec["threshold_value"],
            "severity": spec["severity"],
        }

        events.append(event)

    return events
