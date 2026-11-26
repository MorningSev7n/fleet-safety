import Filters from "@/components/Filters";
import { DailyChart, Empty, Export, Header, int, Kpi, Records, Scores, TypeChart } from "@/components/ui";
import { applyFilters, loadEvents, mean, ranked, readFilters, round0, type Params } from "@/lib/data";
import { ATTENTION_SCORE, calculateDriverScores } from "@/lib/scoring";

export const dynamic = "force-dynamic";

// Driving behaviour (the `driving_events` table): the Streamlit "Driving behaviour" tab.
export default async function Driving({ searchParams }: { searchParams: Promise<Params> }) {
  const [params, rows] = await Promise.all([searchParams, loadEvents("driving")]);
  const { filters, drivers, types, minDate, maxDate } = readFilters(params, rows);
  const filtered = applyFilters(rows, filters);

  // Drivers with no events in the selection keep a score of 100.
  const scoreDrivers = filters.driver ? [filters.driver] : drivers;
  const scores = ranked(calculateDriverScores(filtered, scoreDrivers, filters.from, filters.to));
  const attention = scores.filter((s) => s.score < ATTENTION_SCORE).length;
  const high = filtered.filter((r) => r.severity === "HIGH").length;

  return (
    <div className="page">
      <Header title="Driving behaviour" subtitle={`Harsh braking, cornering and speeding · synthetic demo data · ${filters.from} to ${filters.to}`} />

      {rows.length === 0 ? <Empty>No driving events yet. Run <code>python scripts/seed_behavior.py</code>.</Empty> : (
        <>
          <Filters drivers={drivers} types={types} minDate={minDate} maxDate={maxDate} value={filters} />
          <section className="grid-kpi" aria-label="Key figures">
            <Kpi label="Average score" value={`${round0(mean(scores.map((s) => s.score)))} / 100`} />
            <Kpi label="Driving events" value={int(filtered.length)} />
            <Kpi label="High severity" value={int(high)} color="#F59593" />
            <Kpi label="Need attention" value={`${int(attention)} drivers`} note={`Score below ${ATTENTION_SCORE}`} />
          </section>
          <section className="grid-scores">
            <Scores scores={scores} />
            {filtered.length === 0 ? <Empty>No driving events match these filters.</Empty> : <TypeChart rows={filtered} />}
          </section>
          {filtered.length > 0 && (
            <>
              <DailyChart rows={filtered} filters={filters} />
              <Records area="driving" rows={filtered} filters={filters}><Export area="driving" filters={filters} /></Records>
            </>
          )}
        </>
      )}
    </div>
  );
}
