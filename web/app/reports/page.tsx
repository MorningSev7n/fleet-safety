import { Export, Header } from "@/components/ui";

export default function Reports() {
  return (
    <div className="page">
      <Header title="Reports" subtitle="Download every saved event. Exports keep the raw database values." />
      <section className="grid-2">
        <div className="card">
          <div className="card-head"><h2>Driver monitoring</h2><Export area="events" /></div>
          <p className="muted small" style={{ margin: 0 }}>Webcam events: eyes closed, yawns, looking away, phone use and fatigue.</p>
        </div>
        <div className="card">
          <div className="card-head"><h2>Driving behaviour</h2><Export area="driving" /></div>
          <p className="muted small" style={{ margin: 0 }}>Harsh braking, harsh cornering and speeding (synthetic demo data).</p>
        </div>
      </section>
      <p className="muted small">For a filtered export, set the filters on Overview or Driving behaviour and use Export there.</p>
    </div>
  );
}
