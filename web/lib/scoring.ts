// Port of src/scoring.py. Keep the two in step: same deductions, same thresholds.

export const SEVERITY_DEDUCTIONS = { LOW: 2, MEDIUM: 5, HIGH: 10 } as const;

export const ATTENTION_SCORE = 75;

export type ScoreEvent = {
  timestamp: string | null;
  driver_id: string | null;
  severity: string | null;
};

export type DriverScore = {
  driver_id: string;
  total_events: number;
  low_events: number;
  medium_events: number;
  high_events: number;
  points_deducted: number;
  score: number;
  classification: string;
};

export function getScoreClassification(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 60) return "Needs Improvement";
  return "Poor";
}

// pd.to_datetime(..., errors="coerce").dt.date for the ISO text the app stores; null = NaT.
function eventDate(timestamp: string | null): string | null {
  if (!timestamp || Number.isNaN(Date.parse(timestamp))) return null;
  return timestamp.slice(0, 10);
}

/**
 * Scores from the supplied driving events only. Drivers listed in `drivers`
 * with no events in the period keep 100. Dates are inclusive "YYYY-MM-DD".
 */
export function calculateDriverScores(
  drivingEvents: ScoreEvent[],
  drivers?: (string | null)[],
  startDate?: string,
  endDate?: string,
): DriverScore[] {
  let events = drivingEvents.map((e) => ({
    date: eventDate(e.timestamp),
    driver: e.driver_id,
    severity: (e.severity ?? "").toUpperCase(),
  }));

  // Driver list comes before date filtering so idle drivers still get 100.
  const source = drivers ?? events.map((e) => e.driver);
  const driverList = [...new Set(source.filter((d) => d != null).map(String))].sort();

  if (startDate) events = events.filter((e) => e.date !== null && e.date >= startDate);
  if (endDate) events = events.filter((e) => e.date !== null && e.date <= endDate);

  return driverList.map((driver) => {
    const own = events.filter((e) => String(e.driver) === driver);
    const count = (s: string) => own.filter((e) => e.severity === s).length;
    const low = count("LOW");
    const medium = count("MEDIUM");
    const high = count("HIGH");
    const points =
      low * SEVERITY_DEDUCTIONS.LOW + medium * SEVERITY_DEDUCTIONS.MEDIUM + high * SEVERITY_DEDUCTIONS.HIGH;
    const score = Math.max(0, 100 - points);

    return {
      driver_id: driver,
      total_events: own.length,
      low_events: low,
      medium_events: medium,
      high_events: high,
      points_deducted: points,
      score,
      classification: getScoreClassification(score),
    };
  });
}
