import { query } from "@/lib/db";

// The event's JPEG straight from Postgres (events.snapshot_jpeg), as src/db.py get_latest_snapshot reads it.
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return new Response("Bad id", { status: 400 });

  const [row] = await query<{ snapshot_jpeg: Buffer | null }>(
    "SELECT snapshot_jpeg FROM events WHERE id = $1",
    [Number(id)],
  );
  if (!row?.snapshot_jpeg) return new Response("No snapshot", { status: 404 });

  return new Response(new Uint8Array(row.snapshot_jpeg), {
    // An event's picture never changes, so the browser can keep it.
    headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=86400, immutable" },
  });
}
