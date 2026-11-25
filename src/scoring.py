
"""Calculate demonstration driver-behaviour scores from driving events."""

import pandas as pd


SEVERITY_DEDUCTIONS = {
    "LOW": 2,
    "MEDIUM": 5,
    "HIGH": 10,
}


REQUIRED_COLUMNS = ["timestamp", "driver_id", "severity"]


def get_score_classification(score):
    """Return the classification for a score from 0 to 100."""

    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Needs Improvement"
    else:
        return "Poor"


def calculate_driver_scores(
    driving_events,
    drivers=None,
    start_date=None,
    end_date=None,
):
    """Calculate scores using only the supplied driving-event records.

    ``drivers`` can include drivers with no events in the selected period.
    Those drivers remain in the result with a score of 100.
    Date boundaries are inclusive.
    """

    if driving_events is None:
        driving_events = pd.DataFrame(columns=REQUIRED_COLUMNS)

    if not isinstance(driving_events, pd.DataFrame):
        raise TypeError("driving_events must be a pandas DataFrame")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in driving_events.columns
    ]

    if missing_columns:
        raise ValueError(
            "Driving events are missing required columns: "
            + ", ".join(missing_columns)
        )

    events = driving_events.copy()

    events["timestamp"] = pd.to_datetime(
        events["timestamp"],
        errors="coerce",
    )

    events["severity"] = (
        events["severity"].fillna("").astype(str).str.upper()
    )

    # Get the driver list before date filtering so drivers with no
    # events in the selected period can still receive a score of 100.
    if drivers is None:
        driver_list = sorted(
            events["driver_id"].dropna().astype(str).unique().tolist()
        )
    else:
        driver_list = sorted(
            {str(driver) for driver in drivers if pd.notna(driver)}
        )

    if start_date is not None:
        start_date = pd.Timestamp(start_date).date()

        events = events[
            events["timestamp"].notna()
            & (events["timestamp"].dt.date >= start_date)
        ]

    if end_date is not None:
        end_date = pd.Timestamp(end_date).date()

        events = events[
            events["timestamp"].notna()
            & (events["timestamp"].dt.date <= end_date)
        ]

    results = []

    for driver in driver_list:

        driver_events = events[
            events["driver_id"].astype(str) == driver
        ]

        severity_counts = driver_events["severity"].value_counts()

        low_events = int(severity_counts.get("LOW", 0))
        medium_events = int(severity_counts.get("MEDIUM", 0))
        high_events = int(severity_counts.get("HIGH", 0))

        points_deducted = (
            low_events * SEVERITY_DEDUCTIONS["LOW"]
            + medium_events * SEVERITY_DEDUCTIONS["MEDIUM"]
            + high_events * SEVERITY_DEDUCTIONS["HIGH"]
        )

        score = max(0, 100 - points_deducted)

        results.append({
            "driver_id": driver,
            "total_events": len(driver_events),
            "low_events": low_events,
            "medium_events": medium_events,
            "high_events": high_events,
            "points_deducted": points_deducted,
            "score": score,
            "classification": get_score_classification(score),
        })

    return pd.DataFrame(
        results,
        columns=[
            "driver_id",
            "total_events",
            "low_events",
            "medium_events",
            "high_events",
            "points_deducted",
            "score",
            "classification",
        ],
    )
