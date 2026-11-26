import AutoRefresh from "@/components/AutoRefresh";
import Filters from "@/components/Filters";
import { DailyChart, Empty, Export, Feed, Header, int, Kpi, LivePill, Records, Scores, Snapshot, TypeChart } from "@/components/ui";
import { applyFilters, loadEvents, mean, mostCommon, nice, ranked, readFilters, timeSince, today, type Params } from "@/lib/data";
import { calculateDriverScores } from "@/lib/scoring";
import Link from "next/link";

export const dynamic = "force-dynamic";
const REFRESH_S = 5;

// Driver monitoring (the `events` table): the Streamlit "Driver monitoring" tab.
export default async function Overview({ searchParams }: { searchParams: Promise<Params> }) {
  const [params, events, driving] = await Promise.all([searchParams, loadEvents("events"), loadEvents("driving")]);
  const { filters, drivers, types, minDate, maxDate } = readFilters(params, events);
  const filtered = applyFilters(events, filters);

  const latest = events[0];
  const latestPicture = events.find((r) => r.has_snapshot);
  const todayCount = events.filter((r) => r.timestamp.startsWith(today())).length;
  const high = filtered.filter((r) => r.severity === "HIGH").length;
  const common = mostCommon(filtered);
  const avg = mean(filtered.map((r) => r.duration_s));
  const scores = ranked(calculateDriverScores(driving));

  return (
    <div className="page">
      <AutoRefresh seconds={REFRESH_S} />
      <Header title="Overview" subtitle={`Live webcam detections plus synthetic demo data · ${filters.from} to ${filters.to}`}>
        <LivePill seconds={REFRESH_S} />
      </Header>

      {!latest ? (
        <Empty>No webcam events yet. Run <code>python scripts/seed.py</code> or start the detector.</Empty>
      ) : (
        <>
          <section className="grid-2">
            <div className="card">
              <div className="card-head">
                <h2>Live camera · {latestPicture?.driver_id ?? latest.driver_id}</h2>
                <span className="muted small">{latestPicture?.vehicle_id ?? latest.vehicle_id}</span>
              </div>
              <Snapshot row={latestPicture} />
              <div className="stats">
                <div><span>Last event</span><span>{nice(latest.event_type)}</span></div>
                <div><span>When</span><span>{timeSince(latest.timestamp)}</span></div>
                <div><span>Events today</span><span>{int(todayCount)}</span></div>
              </div>
            </div>
            <div className="card" style={{ gap: 12 }}>
              <div className="card-head">
                <h2>Live feed</h2>
                <Link href="/live" className="small">Open live monitor</Link>
              </div>
              <Feed rows={events.slice(0, 5)} />
            </div>
          </section>

          <Filters drivers={drivers} types={types} minDate={minDate} maxDate={maxDate} value={filters} />

          {filtered.length === 0 ? <Empty>No events match these filters.</Empty> : (
            <>
              <section className="grid-kpi" aria-label="Key figures">
                <Kpi label="Total events" value={int(filtered.length)} note={<><b style={{ color: "var(--text)", fontWeight: 500 }}>{int(todayCount)} today</b> across all drivers</>} />
                <Kpi label="High severity" value={int(high)} color="#F59593" note={`${Math.round((high / filtered.length) * 100)}% of these events`} />
                <Kpi label="Average duration" value={Number.isNaN(avg) ? "—" : `${avg.toFixed(1)} s`} note="Per detected event" />
                <Kpi label="Most common" value={nice(common.type)} note={`${int(common.count)} of ${int(filtered.length)} events`} />
              </section>
              <section className="grid-2">
                <DailyChart rows={filtered} filters={filters} />
                <TypeChart rows={filtered} />
              </section>
              <Records area="events" rows={filtered} filters={filters}><Export area="events" filters={filters} /></Records>
            </>
          )}

          {scores.length > 0 && <Scores scores={scores} note="From driving behaviour events, all dates." />}
        </>
      )}
    </div>
  );
}
