import { test } from "node:test";
import assert from "node:assert/strict";
import { calculateDriverScores, getScoreClassification } from "./scoring.ts";

const events = [
  { timestamp: "2026-11-01T08:00:00", driver_id: "D1", severity: "HIGH" },
  { timestamp: "2026-11-02T08:00:00", driver_id: "D1", severity: "medium" },
  { timestamp: "2026-11-03T08:00:00", driver_id: "D1", severity: "LOW" },
  { timestamp: "2026-11-03T09:00:00", driver_id: "D1", severity: "UNKNOWN" },
  { timestamp: "not a date", driver_id: "D2", severity: "HIGH" },
  ...Array.from({ length: 11 }, () => ({ timestamp: "2026-11-05T08:00:00", driver_id: "D3", severity: "HIGH" })),
];

test("deductions, floor at 0, unknown severities count as events only", () => {
  const [d1, d2, d3] = calculateDriverScores(events);
  assert.deepEqual(d1, {
    driver_id: "D1", total_events: 4, low_events: 1, medium_events: 1, high_events: 1,
    points_deducted: 17, score: 83, classification: "Good",
  });
  assert.equal(d2.score, 90);
  assert.equal(d3.points_deducted, 110);
  assert.equal(d3.score, 0);
});

test("inclusive date range drops bad timestamps; idle listed drivers keep 100", () => {
  const scores = calculateDriverScores(events, ["D2", "D1", "D9", null], "2026-11-02", "2026-11-03");
  assert.deepEqual(scores.map((s) => [s.driver_id, s.score]), [["D1", 93], ["D2", 100], ["D9", 100]]);
});

test("classification thresholds", () => {
  assert.deepEqual([90, 89, 75, 74, 60, 59].map(getScoreClassification),
    ["Excellent", "Good", "Good", "Needs Improvement", "Needs Improvement", "Poor"]);
});
