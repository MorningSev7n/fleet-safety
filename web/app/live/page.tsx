import AutoRefresh from "@/components/AutoRefresh";
import { Empty, Feed, hms, int, Kpi, LivePill, Snapshot } from "@/components/ui";
import { loadEvents, nice, today } from "@/lib/data";
import Link from "next/link";

export const dynamic = "force-dynamic";
const REFRESH_S = 5;

export default async function Live() {
  const events = await loadEvents("events");
  const latest = events[0];
  const todays = events.filter((r) => r.timestamp.startsWith(today()));
  const alert = todays.find((r) => r.severity === "HIGH");

  return (
    <div className="page live-page">
      <AutoRefresh seconds={REFRESH_S} />
      <header className="header" style={{ alignItems: "center" }}>
        <div>
          {latest && <span className="muted" style={{ fontSize: 12 }}>{latest.driver_id} · {latest.vehicle_id}</span>}
          <h1>Live monitor</h1>
        </div>
        <LivePill seconds={REFRESH_S} />
      </header>

      {!latest ? <Empty>Waiting for the first event from the detector…</Empty> : (
        <>
          {alert && (
            <div className="alert" role="alert">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59593" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontWeight: 600, color: "#F8B4B2" }}>
                  {nice(alert.event_type)}{alert.duration_s != null ? ` for ${alert.duration_s.toFixed(2)} s` : ""}
                </span>
                <span style={{ fontSize: 12, color: "var(--text-2)" }}>High severity today · {alert.driver_id} · {hms(alert.timestamp)}</span>
              </div>
            </div>
          )}
          <Snapshot row={events.find((r) => r.has_snapshot)} />
          <section style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
            <Kpi label="Today" value={int(todays.length)} />
            <Kpi label="High today" value={int(todays.filter((r) => r.severity === "HIGH").length)} color="#F59593" />
          </section>
          <div className="card-head">
            <h2>Latest events</h2>
            <Link href="/#records" className="small">See all</Link>
          </div>
          <Feed rows={events.slice(0, 10)} />
        </>
      )}
    </div>
  );
}
