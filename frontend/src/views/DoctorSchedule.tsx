import { useEffect, useState } from "react";
import { authFetch } from "../api";
import { useAuth } from "../AuthContext";
import { appointmentStatusPill } from "./format";

type ScheduleEntry = {
  id: string;
  patient_name: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  reason: string | null;
};

const TODAY_LABEL = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

export function DoctorSchedule() {
  const { token } = useAuth();
  const [entries, setEntries] = useState<ScheduleEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await authFetch("/api/doctors/me/schedule/today", token);
        if (!res.ok) throw new Error("Failed to load schedule");
        const data = await res.json();
        if (!cancelled) setEntries(data);
      } catch (err) {
        console.error(err);
        if (!cancelled) setError("Couldn't load today's schedule. Please try again.");
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
        <h2>Today's Schedule</h2>
        <p>{TODAY_LABEL}</p>
      </div>

      {error && <div className="dash-empty">{error}</div>}
      {!error && entries === null && <div className="dash-empty">Loading…</div>}
      {!error && entries !== null && entries.length === 0 && (
        <div className="dash-empty">Nothing on the schedule for today.</div>
      )}

      {entries?.map(entry => {
        const pill = appointmentStatusPill(entry.status, entry.start_datetime, entry.end_datetime);
        const time = new Date(entry.start_datetime).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
        return (
          <div key={entry.id} className="dash-timeline-row">
            <div className="dash-timeline-time">{time}</div>
            <div className="dash-timeline-card">
              <div>
                <div className="name">{entry.patient_name}</div>
                {entry.reason && <div className="reason">{entry.reason}</div>}
              </div>
              <span className={`dash-status-pill ${pill.className}`}>{pill.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
