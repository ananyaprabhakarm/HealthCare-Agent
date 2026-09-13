import { useEffect, useState } from "react";
import { authFetch } from "../api";
import { useAuth } from "../AuthContext";
import { appointmentStatusPill, formatDateTime } from "./format";

type Appointment = {
  id: string;
  doctor_name: string;
  doctor_specialization: string | null;
  start_datetime: string;
  end_datetime: string;
  status: string;
  reason: string | null;
};

function canCancel(appt: Appointment): boolean {
  return appt.status === "scheduled" && new Date(appt.start_datetime).getTime() > Date.now();
}

export function PatientAppointments() {
  const { token } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await authFetch("/api/patients/me/appointments", token);
        if (!res.ok) throw new Error("Failed to load appointments");
        const data = await res.json();
        if (!cancelled) setAppointments(data);
      } catch (err) {
        console.error(err);
        if (!cancelled) setError("Couldn't load your appointments. Please try again.");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleCancel(appt: Appointment) {
    if (!window.confirm(`Cancel your appointment with ${appt.doctor_name}?`)) return;
    setCancellingId(appt.id);
    try {
      const res = await authFetch(`/api/patients/me/appointments/${appt.id}/cancel`, token, { method: "PATCH" });
      const data = await res.json();
      if (!res.ok) {
        window.alert(data?.detail || "Couldn't cancel this appointment. Please try again.");
        return;
      }
      setAppointments(prev => (prev ? prev.map(a => (a.id === appt.id ? data : a)) : prev));
    } catch (err) {
      console.error(err);
      window.alert("Something went wrong. Please try again.");
    } finally {
      setCancellingId(null);
    }
  }

  return (
    <div>
      <div className="dash-page-head">
        <h2>My Appointments</h2>
        <p>Everything you've booked, past and upcoming.</p>
      </div>

      {error && <div className="dash-empty">{error}</div>}
      {!error && appointments === null && <div className="dash-empty">Loading…</div>}
      {!error && appointments !== null && appointments.length === 0 && (
        <div className="dash-empty">No appointments yet — ask the assistant in Chat to book one.</div>
      )}

      {appointments?.map(appt => {
        const pill = appointmentStatusPill(appt.status, appt.start_datetime, appt.end_datetime);
        return (
          <div key={appt.id} className="dash-appt-row">
            <div className="dash-appt-left">
              <div className="dash-appt-doc">
                {appt.doctor_name}
                {appt.doctor_specialization ? ` — ${appt.doctor_specialization}` : ""}
              </div>
              <div className="dash-appt-time">{formatDateTime(appt.start_datetime)}</div>
            </div>
            <div className="dash-appt-actions">
              {canCancel(appt) && (
                <button className="dash-cancel-btn" onClick={() => handleCancel(appt)} disabled={cancellingId === appt.id}>
                  {cancellingId === appt.id ? "Cancelling…" : "Cancel"}
                </button>
              )}
              <div className={`dash-status-pill ${pill.className}`}>{pill.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
