import { useState } from "react";
import { useAuth } from "./AuthContext";
import { Chat } from "./Chat";
import { PatientAppointments } from "./views/PatientAppointments";
import { FindADoctor } from "./views/FindADoctor";
import { DoctorSchedule } from "./views/DoctorSchedule";
import { DoctorAvailability } from "./views/DoctorAvailability";
import "./pages/dashboard.css";

const PATIENT_NAV = [
  { key: "chat", label: "Chat" },
  { key: "appointments", label: "My Appointments" },
  { key: "doctors", label: "Find a Doctor" }
] as const;

const DOCTOR_NAV = [
  { key: "chat", label: "Chat" },
  { key: "schedule", label: "Today's Schedule" },
  { key: "availability", label: "Manage Availability" }
] as const;

export function AppShell() {
  const { user, logout } = useAuth();
  const isDoctor = user?.role === "doctor";
  const nav = isDoctor ? DOCTOR_NAV : PATIENT_NAV;
  const [activeView, setActiveView] = useState<string>("chat");
  const [chatPrefill, setChatPrefill] = useState("");

  function askInChat(message: string) {
    setChatPrefill(message);
    setActiveView("chat");
  }

  return (
    <div className="dash">
      <div className="dash-shell">
        <aside className="dash-sidebar">
          <div className="dash-brand">
            <img src="/icon-only.svg" alt="" width={24} height={24} />
            health<span>care</span>.agent
          </div>
          <nav>
            {nav.map(item => (
              <button
                key={item.key}
                className={`dash-nav-item ${activeView === item.key ? "active" : ""}`}
                onClick={() => setActiveView(item.key)}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="dash-sidebar-footer">
            <div className="who">
              {user?.name} · {isDoctor ? "Doctor" : "Patient"}
            </div>
            <button className="dash-logout" onClick={logout}>
              Log out
            </button>
          </div>
        </aside>

        <main className="dash-main">
          <div hidden={activeView !== "chat"}>
            <div className="dash-page-head">
              <h2>{isDoctor ? "Ask about your day" : "Ask me anything"}</h2>
              <p>
                {isDoctor
                  ? "Get a quick summary instead of digging through a calendar."
                  : "Check a doctor's availability or book a visit — just describe what you need."}
              </p>
            </div>
            <Chat
              endpoint={isDoctor ? "/api/chat/doctor" : "/api/chat/patient"}
              placeholder={
                isDoctor
                  ? 'e.g. "Who\'s my next patient?"'
                  : 'e.g. "I want to book an appointment with Dr. Ahuja tomorrow morning"'
              }
              prefill={chatPrefill}
            />
          </div>

          {!isDoctor && (
            <>
              <div hidden={activeView !== "appointments"}>
                <PatientAppointments />
              </div>
              <div hidden={activeView !== "doctors"}>
                <FindADoctor onAskInChat={askInChat} />
              </div>
            </>
          )}

          {isDoctor && (
            <>
              <div hidden={activeView !== "schedule"}>
                <DoctorSchedule />
              </div>
              <div hidden={activeView !== "availability"}>
                <DoctorAvailability />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
