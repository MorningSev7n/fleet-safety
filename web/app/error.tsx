"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="page">
      <h1>Could not load the database</h1>
      <p className="muted">Check that DATABASE_URL is set on the server and the database is reachable.</p>
      <p><button type="button" className="btn" onClick={reset}>Try again</button></p>
    </div>
  );
}
