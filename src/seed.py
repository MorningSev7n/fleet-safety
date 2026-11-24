
import random

from db import save_event


# Synthetic drivers and vehicles
DRIVERS = [
    ("DRIVER_001", "VEHICLE_001"),
    ("DRIVER_002", "VEHICLE_002"),
    ("DRIVER_003", "VEHICLE_003"),
    ("DRIVER_004", "VEHICLE_004"),
    ("DRIVER_005", "VEHICLE_005"),
]

# Event types and duration ranges (seconds)
EVENTS = {
    "EYES_CLOSED": (1.5, 5.0),
    "YAWN": (1.0, 4.0),
    "LOOK_AWAY": (2.0, 6.0),
    "PHONE": (1.0, 8.0),
}

SEVERITY = "HIGH"
TOTAL_EVENTS = 40


def seed_database():
    inserted = 0

    # Make sure all four event types appear 10 times.
    event_types = list(EVENTS.keys())
    generated_events = event_types * (TOTAL_EVENTS // len(event_types))

    # Add remaining events if TOTAL_EVENTS changes.
    remaining = TOTAL_EVENTS - len(generated_events)

    for _ in range(remaining):
        generated_events.append(random.choice(event_types))

    # Mix event types randomly.
    random.shuffle(generated_events)

    # Insert synthetic events into the database.
    for event_type in generated_events:

        # Assign 8 events to each driver.
        driver_id, vehicle_id = DRIVERS[inserted % len(DRIVERS)]

        min_duration, max_duration = EVENTS[event_type]

        duration = round(
            random.uniform(min_duration, max_duration), 2
        )

        save_event(
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            event_type=event_type,
            duration_s=duration,
            severity=SEVERITY,
        )

        inserted += 1

    print("\n========== SEED COMPLETE ==========")
    print(f"Synthetic events inserted: {inserted}")
    print(f"Drivers available: {len(DRIVERS)}")
    print(f"Event types available: {len(EVENTS)}")
    print(f"Severity: {SEVERITY}")
    print("===================================\n")


if __name__ == "__main__":
    seed_database()
