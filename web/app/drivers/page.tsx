import { Empty, Header, Scores } from "@/components/ui";
import { loadEvents, ranked } from "@/lib/data";
import { calculateDriverScores } from "@/lib/scoring";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Drivers() {
  const scores = ranked(calculateDriverScores(await loadEvents("driving")));
  return (
    <div className="page">
      <Header title="Drivers" subtitle="Scores from all driving behaviour events. Filter by date on Driving behaviour." />
      {scores.length === 0 ? <Empty>No driving events yet. Run <code>python scripts/seed_behavior.py</code>.</Empty> : <Scores scores={scores} />}
      <p className="muted small"><Link href="/driving">Open driving behaviour</Link> to filter by driver, event type or date.</p>
    </div>
  );
}
