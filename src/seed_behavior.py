
from collections import Counter

from db import (
    get_driving_events,
    save_driving_events,
)

from driving_behavior import (
    generate_driving_events,
)


def main():
    """Generate and save the synthetic driving events."""

    existing_events = get_driving_events()

    if not existing_events.empty:
        print(
            "Driving events already exist. "
            "No new events were inserted."
        )
        print(
            f"Existing driving events: {len(existing_events)}"
        )
        return

    events = generate_driving_events()

    # Check total event count
    if len(events) != 40:
        raise ValueError(
            f"Expected 40 events, but generated {len(events)}."
        )

    # Check behaviour distribution
    event_counts = Counter(
        event["event_type"] for event in events
    )

    expected_event_counts = {
        "HARSH_BRAKING": 14,
        "HARSH_CORNERING": 13,
        "SPEEDING": 13,
    }

    if dict(event_counts) != expected_event_counts:
        raise ValueError(
            f"Unexpected event distribution: {dict(event_counts)}"
        )

    # Check driver distribution
    driver_counts = Counter(
        event["driver_id"] for event in events
    )

    if len(driver_counts) != 5:
        raise ValueError("Expected exactly five drivers.")

    if any(count != 8 for count in driver_counts.values()):
        raise ValueError(
            f"Each driver must have 8 events: {dict(driver_counts)}"
        )

    # Insert all 40 events in one database transaction.
    save_driving_events(events)

    print("Synthetic driving events inserted successfully.")
    print(f"Total events: {len(events)}")

    print("\nEvents by behaviour:")
    for event_type, count in sorted(event_counts.items()):
        print(f"{event_type}: {count}")

    print("\nEvents by driver:")
    for driver_id, count in sorted(driver_counts.items()):
        print(f"{driver_id}: {count}")


if __name__ == "__main__":
    main()
