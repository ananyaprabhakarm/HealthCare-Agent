import { Chat } from "./Chat";

export function PatientView() {
  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ fontSize: "1.25rem", fontWeight: 600, color: "#e5e7eb" }}>Patient assistant</div>
        <div style={{ fontSize: "0.9rem", color: "#9ca3af", marginTop: "0.25rem" }}>Ask in natural language to check availability and book appointments.</div>
      </div>
      <Chat endpoint="/api/chat/patient" placeholder='e.g. "I want to book an appointment with Dr. Ahuja tomorrow morning"' />
    </div>
  );
}


