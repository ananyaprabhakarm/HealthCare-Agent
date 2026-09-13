export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function formatTimeStr(hms: string): string {
  const [h, m] = hms.split(":").map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export const WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export function appointmentStatusPill(status: string, startIso: string, endIso: string): { label: string; className: string } {
  if (status === "cancelled") return { label: "Cancelled", className: "cancelled" };
  if (status === "no_show") return { label: "No-show", className: "cancelled" };
  if (status === "completed") return { label: "Completed", className: "done" };

  const now = Date.now();
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (now >= start && now <= end) return { label: "In progress", className: "progress" };
  if (now > end) return { label: "Past", className: "done" };
  return { label: "Upcoming", className: "upcoming" };
}
