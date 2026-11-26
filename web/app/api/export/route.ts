import { applyFilters, bySeverity, exportFile, FORMATS, loadEvents, readFilters, type Area, type Format } from "@/lib/data";

// /api/export?area=events|driving&format=csv|tsv|xml plus the page's filters.
export async function GET(req: Request) {
  const params = Object.fromEntries(new URL(req.url).searchParams);
  const area = params.area as Area;
  const format = params.format as Format;
  if (!["events", "driving"].includes(area) || !(format in FORMATS)) {
    return new Response("Unknown area or format", { status: 400 });
  }

  const rows = await loadEvents(area);
  const { filters } = readFilters(params, rows);
  const body = exportFile(bySeverity(applyFilters(rows, filters), filters.sev), area, format);
  const name = area === "events" ? "webcam_events" : "driving_events";

  return new Response(body, {
    headers: {
      "Content-Type": `${FORMATS[format]}; charset=utf-8`,
      "Content-Disposition": `attachment; filename="${name}.${format}"`,
    },
  });
}
