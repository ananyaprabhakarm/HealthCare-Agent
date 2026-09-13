import { useEffect, useMemo, useState } from "react";
import { authFetch } from "../api";
import { useAuth } from "../AuthContext";

type Doctor = {
  id: string;
  name: string;
  specialization: string | null;
  available_today: boolean;
};

type FindADoctorProps = {
  onAskInChat: (message: string) => void;
};

export function FindADoctor({ onAskInChat }: FindADoctorProps) {
  const { token } = useAuth();
  const [doctors, setDoctors] = useState<Doctor[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("All");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await authFetch("/api/doctors", token);
        if (!res.ok) throw new Error("Failed to load doctors");
        const data = await res.json();
        if (!cancelled) setDoctors(data);
      } catch (err) {
        console.error(err);
        if (!cancelled) setError("Couldn't load the doctor directory. Please try again.");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const specializations = useMemo(() => {
    const set = new Set<string>();
    (doctors ?? []).forEach(d => {
      if (d.specialization) set.add(d.specialization);
    });
    return Array.from(set).sort();
  }, [doctors]);

  const filtered = useMemo(() => {
    if (!doctors) return [];
    if (filter === "All") return doctors;
    if (filter === "Available today") return doctors.filter(d => d.available_today);
    return doctors.filter(d => d.specialization === filter);
  }, [doctors, filter]);

  return (
    <div>
      <div className="dash-page-head">
        <h2>Find a Doctor</h2>
        <p>Browse by specialty or see who's free today.</p>
      </div>

      <div className="dash-filter-row">
        {["All", "Available today", ...specializations].map(chip => (
          <button
            key={chip}
            className={`dash-filter-chip ${filter === chip ? "on" : ""}`}
            onClick={() => setFilter(chip)}
          >
            {chip}
          </button>
        ))}
        <button className="dash-filter-chip inert" title="Coming soon — ratings aren't collected yet" disabled>
          Top rated
        </button>
      </div>

      {error && <div className="dash-empty">{error}</div>}
      {!error && doctors === null && <div className="dash-empty">Loading…</div>}
      {!error && doctors !== null && filtered.length === 0 && (
        <div className="dash-empty">No doctors match that filter.</div>
      )}

      <div className="dash-grid">
        {filtered.map(doc => (
          <div key={doc.id} className="dash-card">
            <div className="dash-card-top">
              <div>
                <h4>{doc.name}</h4>
                <div className="spec">{doc.specialization || "General"}</div>
              </div>
              <span className={`dash-badge ${doc.available_today ? "available" : "busy"}`}>
                {doc.available_today ? "Available today" : "Not available today"}
              </span>
            </div>
            <div className="dash-card-actions">
              <button className="primary" onClick={() => onAskInChat(`I'd like to book an appointment with ${doc.name}`)}>
                Book
              </button>
              <button onClick={() => onAskInChat(`What availability does ${doc.name} have?`)}>View slots</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
