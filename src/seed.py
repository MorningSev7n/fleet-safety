
import random
from collections import Counter

from db import save_event
from severity import SEVERITY_RULES, classify_severity


# Synthetic drivers and vehicles
DRIVERS = [
    ("DRIVER_001", "VEHICLE_001"),
    ("DRIVER_002", "VEHICLE_002"),
    ("DRIVER_003", "VEHICLE_003"),
    ("DRIVER_004", "VEHICLE_004"),
    ("DRIVER_005", "VEHICLE_005"),
]

TOTAL_EVENTS = 40

SEVERITY_LEVELS = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


def generate_duration(event_type, severity):
    """Generate a duration matching the requested severity."""

    rules = SEVERITY_RULES[event_type]

    if severity == "LOW":

        minimum = rules["minimum"]
        maximum = rules["medium"] - 0.01

    elif severity == "MEDIUM":

        minimum = rules["medium"]
        maximum = rules["high"] - 0.01

    else:

        minimum = rules["high"]
        maximum = rules["maximum"]

    return round(
        random.uniform(minimum, maximum),
        2
    )


def seed_database():

    inserted = 0
    severity_counts = Counter()
    event_counts = Counter()

    event_types = list(SEVERITY_RULES.keys())

    if TOTAL_EVENTS % len(event_types) != 0:
        raise ValueError(
            "TOTAL_EVENTS must be divisible by the number of event types."
        )

    events_per_type = TOTAL_EVENTS // len(event_types)

    generated_events = []

    # Generate an equal number of each event type.
    for event_type in event_types:

        for index in range(events_per_type):

            # Rotate severity levels to ensure all three
            # appear in the synthetic dataset.
            severity = SEVERITY_LEVELS[
                index % len(SEVERITY_LEVELS)
            ]

            generated_events.append(
                (event_type, severity)
            )

    # Mix the events randomly.
    random.shuffle(generated_events)

    # Insert synthetic events.
    for event_type, expected_severity in generated_events:

        driver_id, vehicle_id = DRIVERS[
            inserted % len(DRIVERS)
        ]

        duration = generate_duration(
            event_type,
            expected_severity
        )

        severity = classify_severity(
            event_type,
            duration
        )

        save_event(
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            event_type=event_type,
            duration_s=duration,
            severity=severity,
        )

        inserted += 1

        severity_counts[severity] += 1
        event_counts[event_type] += 1

    print("\n========== SEED COMPLETE ==========")

    print(f"Synthetic events inserted: {inserted}")
    print(f"Drivers available: {len(DRIVERS)}")

    print("\nEvent distribution:")

    for event_type, count in sorted(event_counts.items()):
        print(f"{event_type}: {count}")

    print("\nSeverity distribution:")

    for severity in SEVERITY_LEVELS:
        print(
            f"{severity}: {severity_counts[severity]}"
        )

    print("===================================\n")


if __name__ == "__main__":
    seed_database()
