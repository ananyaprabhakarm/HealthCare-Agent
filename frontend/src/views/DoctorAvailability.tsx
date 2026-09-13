import { useEffect, useState } from "react";
import { authFetch } from "../api";
import { useAuth } from "../AuthContext";
import { WEEKDAY_NAMES, formatTimeStr } from "./format";

type AvailabilityEntry = {
  day_of_week: number;
  start_time: string;
  end_time: string;
};

export function DoctorAvailability() {
  const { token } = useAuth();
  const [entries, setEntries] = useState<AvailabilityEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await authFetch("/api/doctors/me/availability", token);
        if (!res.ok) throw new Error("Failed to load availability");
        const data = await res.json();
        if (!cancelled) setEntries(data);
      } catch (err) {
        console.error(err);
        if (!cancelled) setError("Couldn't load your availability. Please try again.");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div>
      <div className="dash-page-head">
        <h2>Manage Availability</h2>
        <p>Set your weekly hours — this is what patients can book against. Editing is coming soon; this is read-only for now.</p>
      </div>

      {error && <div className="dash-empty">{error}</div>}
      {!error && entries === null && <div className="dash-empty">Loading…</div>}

      {!error && entries !== null && (
        <div className="dash-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px,1fr))", maxWidth: 700 }}>
          {WEEKDAY_NAMES.map((day, index) => {
            const entry = entries.find(e => e.day_of_week === index);
            return (
              <div key={day} className="dash-card">
                <h4>{day}</h4>
                <div className="spec">
                  {entry ? `${formatTimeStr(entry.start_time)} – ${formatTimeStr(entry.end_time)}` : "Not available"}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
