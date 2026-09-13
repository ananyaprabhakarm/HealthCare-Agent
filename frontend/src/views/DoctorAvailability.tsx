import { FormEvent, useEffect, useState } from "react";
import { authFetch } from "../api";
import { useAuth } from "../AuthContext";
import { WEEKDAY_NAMES, formatTimeStr } from "./format";

type AvailabilityEntry = {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
};

export function DoctorAvailability() {
  const { token } = useAuth();
  const [entries, setEntries] = useState<AvailabilityEntry[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      const res = await authFetch("/api/doctors/me/availability", token);
      if (!res.ok) throw new Error("Failed to load availability");
      const data = await res.json();
      setEntries(data);
    } catch (err) {
      console.error(err);
      setLoadError("Couldn't load your availability. Please try again.");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const res = await authFetch("/api/doctors/me/availability", token, {
        method: "POST",
        body: JSON.stringify({ day_of_week: dayOfWeek, start_time: startTime, end_time: endTime })
      });
      const data = await res.json();
      if (!res.ok) {
        setFormError(data?.detail || "Failed to add this slot. Please try again.");
        await load();
        return;
      }
      setEntries(prev => (prev ? [...prev, data] : [data]));
    } catch (err) {
      console.error(err);
      setFormError("Something went wrong. Please try again.");
      await load();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(id: string) {
    const previous = entries;
    setEntries(prev => (prev ? prev.filter(e => e.id !== id) : prev));
    try {
      const res = await authFetch(`/api/doctors/me/availability/${id}`, token, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to remove slot");
    } catch (err) {
      console.error(err);
      setEntries(previous ?? null);
    }
  }

  return (
    <div>
      <div className="dash-page-head">
        <h2>Manage Availability</h2>
        <p>Set your weekly hours — this is what patients can book against.</p>
      </div>

      <form className="dash-availability-form" onSubmit={handleAdd}>
        <div className="field">
          <label htmlFor="avail-day">Day</label>
          <select id="avail-day" value={dayOfWeek} onChange={e => setDayOfWeek(Number(e.target.value))}>
            {WEEKDAY_NAMES.map((day, index) => (
              <option key={day} value={index}>
                {day}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="avail-start">From</label>
          <input id="avail-start" type="time" value={startTime} onChange={e => setStartTime(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="avail-end">To</label>
          <input id="avail-end" type="time" value={endTime} onChange={e => setEndTime(e.target.value)} required />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Adding…" : "Add"}
        </button>
      </form>
      {formError && <div className="dash-form-error">{formError}</div>}

      {loadError && <div className="dash-empty">{loadError}</div>}
      {!loadError && entries === null && <div className="dash-empty">Loading…</div>}

      {!loadError && entries !== null && (
        <div className="dash-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px,1fr))", maxWidth: 700 }}>
          {WEEKDAY_NAMES.map((day, index) => {
            const dayEntries = entries.filter(e => e.day_of_week === index);
            return (
              <div key={day} className="dash-card">
                <h4>{day}</h4>
                {dayEntries.length === 0 && <div className="spec">Not available</div>}
                {dayEntries.map(entry => (
                  <div key={entry.id}>
                    <div className="spec">
                      {formatTimeStr(entry.start_time)} – {formatTimeStr(entry.end_time)}
                    </div>
                    <button className="remove-btn" onClick={() => handleRemove(entry.id)}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
