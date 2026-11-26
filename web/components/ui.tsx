// Server components shared by the pages. Charts are plain CSS bars.
import Link from "next/link";
import { ATTENTION_SCORE, SEVERITY_DEDUCTIONS, type DriverScore } from "@/lib/scoring";
import { dateOf, nice, qs, SEVERITY_COLORS, SEVERITY_ORDER, type Area, type EventRow, type Filters } from "@/lib/data";

const sevColor = (s: string) => SEVERITY_COLORS[s] ?? { bar: "#6F7A8B", text: "#C8CFDA", tint: "rgba(111,122,139,0.16)" };
const fmtDay = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
export const hms = (ts: string) => ts.slice(11, 19);
export const dayTime = (ts: string) => `${fmtDay(ts.slice(0, 10))} ${hms(ts)}`;
export const int = (n: number) => n.toLocaleString("en-US");

export function Header({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <header className="header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      <div className="actions">{children}</div>
    </header>
  );
}

export const LivePill = ({ seconds }: { seconds: number }) => (
  <span className="pill-live"><span className="dot" />Live · refreshes every {seconds} s</span>
);

export function Kpi({ label, value, note, color }: { label: string; value: string; note?: React.ReactNode; color?: string }) {
  return (
    <div className="card kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value num" style={{ color }}>{value}</div>
      {note && <div className="muted small">{note}</div>}
    </div>
  );
}

export function Badge({ severity }: { severity: string }) {
  const c = sevColor(severity);
  return <span className="badge" style={{ background: c.tint, color: c.text }}>{nice(severity)}</span>;
}

export function Export({ area, filters }: { area: Area; filters?: Filters }) {
  const q = (format: string) => `/api/export${qs({ area, format, ...filters })}`;
  return (
    <details className="export">
      <summary className="btn btn-primary">
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" /></svg>
        Export
      </summary>
      <div className="export-menu">
        <a href={q("csv")} download>CSV</a>
        <a href={q("tsv")} download>TSV</a>
        <a href={q("xml")} download>XML</a>
      </div>
    </details>
  );
}

export const Empty = ({ children }: { children: React.ReactNode }) => <div className="empty">{children}</div>;

/** Events per day, every day from the first to the last event so gaps show. Each bar links to that day. */
export function DailyChart({ rows, filters, title = "Events per day" }: { rows: EventRow[]; filters: Filters; title?: string }) {
  const counts = new Map<string, number>();
  for (const r of rows) counts.set(dateOf(r), (counts.get(dateOf(r)) ?? 0) + 1);
  const dates = [...counts.keys()].sort();
  const days: string[] = [];
  for (let d = new Date(`${dates[0]}T00:00:00Z`); dates.length && d <= new Date(`${dates.at(-1)}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + 1)) {
    days.push(d.toISOString().slice(0, 10));
  }
  const max = Math.max(1, ...counts.values());
  const peak = dates.find((d) => counts.get(d) === max);
  return (
    <div className="card">
      <div className="card-head">
        <h2>{title}</h2>
        <span className="muted small">Click a day to filter</span>
      </div>
      <div className="daily" role="img" aria-label={`${title}. Peak of ${max} events on ${peak ? fmtDay(peak) : "—"}.`}>
        {days.map((d, i) => {
          const n = counts.get(d) ?? 0;
          return (
            <Link key={d} href={qs({ ...filters, from: d, to: d })} scroll={false} title={`${fmtDay(d)}: ${n} events`} className={i === days.length - 1 ? "last" : undefined}>
              <span style={{ height: n ? `${(n / max) * 100}%` : "2px" }} />
            </Link>
          );
        })}
      </div>
      <div className="axis">
        <span>{days[0] && fmtDay(days[0])}</span>
        {days.length > 2 && <span>{fmtDay(days[Math.floor(days.length / 2)])}</span>}
        <span>{days.length > 1 && fmtDay(days.at(-1)!)}</span>
      </div>
    </div>
  );
}

/** Events per type split by severity, biggest first, legend above. */
export function TypeChart({ rows }: { rows: EventRow[] }) {
  const types = new Map<string, Record<string, number>>();
  for (const r of rows) {
    const t = types.get(r.event_type) ?? {};
    t[r.severity] = (t[r.severity] ?? 0) + 1;
    types.set(r.event_type, t);
  }
  const total = (t: Record<string, number>) => Object.values(t).reduce((a, b) => a + b, 0);
  const list = [...types].sort((a, b) => total(b[1]) - total(a[1]) || a[0].localeCompare(b[0]));
  const max = Math.max(1, ...list.map(([, t]) => total(t)));
  return (
    <div className="card">
      <div className="card-head">
        <h2>By event type</h2>
        <div className="legend">
          {SEVERITY_ORDER.map((s) => <span key={s}><span className="swatch" style={{ background: SEVERITY_COLORS[s].bar }} />{nice(s)}</span>)}
        </div>
      </div>
      <div className="types">
        {list.map(([type, t]) => {
          const sum = total(t);
          const parts = [...SEVERITY_ORDER, ...Object.keys(t).filter((s) => !SEVERITY_ORDER.includes(s as never))];
          return (
            <div key={type} className="type-row">
              <span style={{ color: "var(--text-2)", fontSize: 13 }}>{nice(type)}</span>
              <div className="stack" style={{ width: `${(sum / max) * 100}%` }}
                title={parts.filter((s) => t[s]).map((s) => `${nice(s)}: ${t[s]}`).join(", ")}>
                {parts.map((s) => t[s] ? <div key={s} style={{ flex: t[s], background: sevColor(s).bar }} /> : null)}
              </div>
              <span className="muted small tabular right">{sum}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const scoreColor = (score: number) => (score >= ATTENTION_SCORE ? "var(--good)" : score >= 60 ? "#EDB45E" : "#F59593");

export function Scores({ scores, title = "Driver scores", note }: { scores: DriverScore[]; title?: string; note?: string }) {
  const deductions = SEVERITY_ORDER.map((s) => `${nice(s)} −${SEVERITY_DEDUCTIONS[s]}`).join(", ");
  return (
    <div className="card" style={{ gap: 4 }}>
      <div className="card-head" style={{ paddingBottom: 8 }}>
        <h2>{title}</h2>
        <span className="muted" style={{ fontSize: 12 }}>Below {ATTENTION_SCORE} needs attention</span>
      </div>
      {scores.map((d) => (
        <div key={d.driver_id} className="score-row">
          <div className="avatar" aria-hidden="true">{initials(d.driver_id)}</div>
          <div className="score-main">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontWeight: 500 }}>{d.driver_id}</span>
              <span className="tabular" style={{ fontWeight: 600 }}>{d.score}</span>
            </div>
            <div className="track"><div style={{ width: `${d.score}%`, background: scoreColor(d.score) }} /></div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: scoreColor(d.score) }}>{d.classification}</span>
              <span className="counts tabular"><span>Low {d.low_events}</span><span>Medium {d.medium_events}</span><span>High {d.high_events}</span></span>
            </div>
          </div>
        </div>
      ))}
      <p className="muted" style={{ fontSize: 12, margin: "12px 0 0" }}>
        {note ? `${note} ` : ""}Each driver starts at 100. Deductions: {deductions}. Synthetic demo rules, not a certified safety rating.
      </p>
    </div>
  );
}

function initials(id: string) {
  const digits = id.match(/\d+/)?.[0];
  return digits ? `D${Number(digits)}` : id.slice(0, 2).toUpperCase();
}

/** Records with severity chips (they filter this table and the export, not the KPIs). */
export function Records({ area, rows, filters, children }: { area: Area; rows: EventRow[]; filters: Filters; children?: React.ReactNode }) {
  const shown = filters.sev ? rows.filter((r) => r.severity === filters.sev) : rows;
  return (
    <div id="records" className="card">
      <div className="card-head">
        <div>
          <h2>Records</h2>
          <span className="muted small">{int(shown.length)} {filters.sev ? `${nice(filters.sev).toLowerCase()} ` : ""}events match your filters · newest first</span>
        </div>
        <div className="actions">
          <div className="chips" role="group" aria-label="Filter by severity">
            {["", "HIGH", "MEDIUM", "LOW"].map((s) => (
              <Link key={s || "all"} href={`${qs({ ...filters, sev: s })}#records`} scroll={false} className="chip" aria-current={filters.sev === s ? "true" : undefined}>
                {s ? nice(s) : "All"}
              </Link>
            ))}
          </div>
          {children}
        </div>
      </div>
      {shown.length === 0 ? <Empty>No events match these filters.</Empty> : (
        <div className="table-wrap">
          <table>
            <thead>
              {area === "events" ? (
                <tr><th scope="col">Snapshot</th><th scope="col">Time</th><th scope="col">Driver</th><th scope="col">Vehicle</th><th scope="col">Event</th><th scope="col" className="right">Duration (s)</th><th scope="col">Severity</th></tr>
              ) : (
                <tr><th scope="col">Time</th><th scope="col">Driver</th><th scope="col">Vehicle</th><th scope="col">Event</th><th scope="col" className="right">Measured</th><th scope="col" className="right">Limit</th><th scope="col">Unit</th><th scope="col">Severity</th></tr>
              )}
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id}>
                  {area === "events" && (
                    <td>{r.has_snapshot
                      // eslint-disable-next-line @next/next/no-img-element
                      ? <a href={`/api/snapshot/${r.id}`} target="_blank"><img className="thumb" src={`/api/snapshot/${r.id}`} alt={`Snapshot: ${nice(r.event_type)}`} loading="lazy" /></a>
                      : <span style={{ color: "var(--faint)" }}>—</span>}</td>
                  )}
                  <td className="tabular" style={{ color: "var(--text-2)" }}>{dayTime(r.timestamp)}</td>
                  <td>{r.driver_id}</td>
                  <td>{r.vehicle_id}</td>
                  <td>{nice(r.event_type)}</td>
                  {area === "events" ? (
                    <td className="right tabular">{r.duration_s?.toFixed(2) ?? "—"}</td>
                  ) : (
                    <>
                      <td className="right tabular">{r.measured_value?.toFixed(2) ?? "—"}</td>
                      <td className="right tabular">{r.threshold_value?.toFixed(2) ?? "—"}</td>
                      <td>{r.unit ?? "—"}</td>
                    </>
                  )}
                  <td><Badge severity={r.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** Latest events for the live feed (unfiltered, like the Streamlit live panel). */
export function Feed({ rows }: { rows: EventRow[] }) {
  return (
    <div className="feed">
      {rows.map((r) => {
        const c = sevColor(r.severity);
        return (
          <div key={r.id} className="feed-row">
            <div className="feed-icon" style={{ background: c.tint, color: c.text }}>
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
            </div>
            <div className="feed-main">
              <span style={{ fontWeight: 600 }}>{nice(r.event_type)}</span>
              <span className="muted small">{r.driver_id}{r.duration_s != null ? ` · ${r.duration_s.toFixed(2)} s` : ""}</span>
            </div>
            <div className="feed-side">
              <Badge severity={r.severity} />
              <span className="muted tabular" style={{ fontSize: 12 }}>{hms(r.timestamp)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Newest event that has a picture, served from Postgres by /api/snapshot/<id>. */
export function Snapshot({ row }: { row?: EventRow }) {
  if (!row) {
    return <div className="snap"><span className="small">No snapshot yet</span></div>;
  }
  const c = sevColor(row.severity);
  return (
    <div className="snap">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/api/snapshot/${row.id}`} alt={`Latest snapshot: ${nice(row.event_type)} at ${hms(row.timestamp)}`} />
      <div className="tags">
        <span className="tag">{nice(row.event_type)}</span>
        <span className="tag" style={{ background: c.bar, color: "var(--ground)", fontWeight: 600 }}>{nice(row.severity)}</span>
      </div>
      <span className="time tabular">{dayTime(row.timestamp)}</span>
    </div>
  );
}
