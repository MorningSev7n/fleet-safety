// Client-safe helpers (no database import).

/** EYES_CLOSED -> Eyes closed. Display only; exports keep raw values. */
export const nice = (value: unknown) => {
  const s = String(value).replaceAll("_", " ");
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
};
