// Loading, filtering and formatting shared by the pages and the export route.
// Mirrors src/dashboard.py so both dashboards show the same numbers.
import { query } from "./db";

// Timestamps are saved in the detector's local time with no offset, and Vercel runs in UTC,
// so read them (and "today") in the detector's zone. Override with DATA_TZ if the device moves.
process.env.TZ = process.env.DATA_TZ ?? "Asia/Manila";

export type Area = "events" | "driving";

export type EventRow = {
  id: number;
  timestamp: string;
  driver_id: string;
  vehicle_id: string;
  event_type: string;
  severity: string;
  // events (driver monitoring)
  duration_s?: number | null;
  snapshot?: string | null;
  has_snapshot?: boolean;
  // driving_events
  measured_value?: number | null;
  threshold_value?: number | null;
  unit?: string | null;
};

export const SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"] as const;

export const SEVERITY_COLORS: Record<string, { bar: string; text: string; tint: string }> = {
  LOW: { bar: "#7FB3E8", text: "#8EC0F0", tint: "rgba(127,179,232,0.14)" },
  MEDIUM: { bar: "#E7A947", text: "#EDB45E", tint: "rgba(231,169,71,0.14)" },
  HIGH: { bar: "#E35D5B", text: "#F59593", tint: "rgba(227,93,91,0.16)" },
};

const DRIVING_UNITS: Record<string, string> = {
  HARSH_BRAKING: "m/s²",
  HARSH_CORNERING: "m/s²",
  SPEEDING: "km/h",
};

// Export columns: same order and raw values as the Streamlit exports.
export const EXPORT_COLUMNS: Record<Area, (keyof EventRow)[]> = {
  events: ["id", "timestamp", "driver_id", "vehicle_id", "event_type", "duration_s", "severity", "snapshot"],
  driving: ["id", "timestamp", "driver_id", "vehicle_id", "event_type", "measured_value", "threshold_value", "unit", "severity"],
};

export { nice } from "./labels";

const validTime = (r: EventRow) => !Number.isNaN(Date.parse(r.timestamp));
const num = (v: unknown) => (v == null || v === "" ? null : Number(v));

// shortcut: loads whole tables like the Streamlit app; move filters into SQL once a fleet has ~100k events.
export async function loadEvents(area: Area): Promise<EventRow[]> {
  if (area === "events") {
    // Picture bytes stay out; has_snapshot says whether /api/snapshot/<id> has one.
    const rows = await query<EventRow>(`
      SELECT id, timestamp, driver_id, vehicle_id, event_type, duration_s, severity, snapshot,
             snapshot_jpeg IS NOT NULL AS has_snapshot
      FROM events ORDER BY timestamp DESC`);
    return rows.filter(validTime).map((r) => ({ ...r, duration_s: num(r.duration_s) }));
  }
  const rows = await query<EventRow>("SELECT * FROM driving_events ORDER BY timestamp DESC");
  return rows.filter(validTime).map((r) => ({
    ...r,
    measured_value: num(r.measured_value),
    threshold_value: num(r.threshold_value),
    unit: DRIVING_UNITS[r.event_type] ?? null,
  }));
}

export const dateOf = (r: EventRow) => r.timestamp.slice(0, 10);

/** Server-local calendar date, as Python's date.today(). */
export function today() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export type Filters = { driver: string; type: string; from: string; to: string; sev: string };
export type Params = Record<string, string | string[] | undefined>;

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const isDate = (v: string) => /^\d{4}-\d{2}-\d{2}$/.test(v);

/** Read filters from the URL. Default range: first event to max(last event, today). */
export function readFilters(params: Params, rows: EventRow[]) {
  const dates = rows.map(dateOf).sort();
  const minDate = dates[0] ?? today();
  const maxDate = [dates.at(-1) ?? "", today()].sort()[1];
  const from = one(params.from);
  const to = one(params.to);
  const sev = one(params.sev).toUpperCase();
  const filters: Filters = {
    driver: one(params.driver),
    type: one(params.type),
    from: isDate(from) ? from : minDate,
    to: isDate(to) ? to : maxDate,
    sev: (SEVERITY_ORDER as readonly string[]).includes(sev) ? sev : "",
  };
  return {
    filters,
    minDate,
    maxDate,
    drivers: [...new Set(rows.map((r) => r.driver_id))].sort(),
    types: [...new Set(rows.map((r) => r.event_type))].sort(),
  };
}

export function applyFilters(rows: EventRow[], f: Filters) {
  return rows.filter(
    (r) =>
      dateOf(r) >= f.from &&
      dateOf(r) <= f.to &&
      (!f.driver || r.driver_id === f.driver) &&
      (!f.type || r.event_type === f.type),
  );
}

export const bySeverity = (rows: EventRow[], sev: string) => (sev ? rows.filter((r) => r.severity === sev) : rows);

/** pandas value_counts().idxmax(): highest count, first seen wins a tie. */
export function mostCommon(rows: EventRow[]) {
  const counts = new Map<string, number>();
  for (const r of rows) counts.set(r.event_type, (counts.get(r.event_type) ?? 0) + 1);
  let best = "";
  let bestCount = 0;
  for (const [k, v] of counts) if (v > bestCount) [best, bestCount] = [k, v];
  return { type: best, count: bestCount };
}

/** Python's f"{x:.0f}" rounds exact halves to even; toFixed rounds them up. */
export function round0(x: number) {
  const r = Math.round(x);
  return x - Math.floor(x) === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

export function mean(values: (number | null | undefined)[]) {
  const v = values.filter((x): x is number => x != null && !Number.isNaN(x));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN;
}

export function timeSince(timestamp: string) {
  const s = Math.max(Math.floor((Date.now() - Date.parse(timestamp)) / 1000), 0);
  if (s < 60) return `${s} s ago`;
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min ago`;
}

// ---------- exports ----------

export const FORMATS = {
  csv: "text/csv",
  tsv: "text/tab-separated-values",
  xml: "application/xml",
} as const;
export type Format = keyof typeof FORMATS;

const cell = (v: unknown) => (v == null ? "" : String(v));

function delimited(rows: EventRow[], cols: (keyof EventRow)[], sep: string) {
  // RFC 4180 quoting, as pandas to_csv does.
  const q = (v: unknown) => {
    const s = cell(v);
    return /["\r\n]/.test(s) || s.includes(sep) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  return [cols.join(sep), ...rows.map((r) => cols.map((c) => q(r[c])).join(sep))].join("\n") + "\n";
}

function xml(rows: EventRow[], cols: (keyof EventRow)[]) {
  const esc = (v: unknown) =>
    cell(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const body = rows
    .map((r) => `    <event>\n${cols.map((c) => `        <${c}>${esc(r[c])}</${c}>`).join("\n")}\n    </event>`)
    .join("\n");
  return `<?xml version='1.0' encoding='utf-8'?>\n<fleet_events total_records="${rows.length}">\n${body}\n</fleet_events>\n`;
}

export function exportFile(rows: EventRow[], area: Area, format: Format) {
  const cols = EXPORT_COLUMNS[area];
  if (format === "xml") return xml(rows, cols);
  return delimited(rows, cols, format === "tsv" ? "\t" : ",");
}

/** Query string for links that keep the current filters. */
export function qs(f: Partial<Filters> & Record<string, string | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(f)) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
}

/** Dashboard order: best score first, then driver id. */
export const ranked = <T extends { score: number; driver_id: string }>(s: T[]) =>
  [...s].sort((a, b) => b.score - a.score || (a.driver_id < b.driver_id ? -1 : a.driver_id > b.driver_id ? 1 : 0));
