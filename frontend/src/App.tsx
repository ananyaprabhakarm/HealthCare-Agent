import { useState } from "react";
import { DoctorView } from "./DoctorView";
import { PatientView } from "./PatientView";

export default function App() {
  const [role, setRole] = useState<"patient" | "doctor">("patient");
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", fontFamily: "system-ui, sans-serif", background: "#0f172a", color: "#e5e7eb" }}>
      <header style={{ padding: "1rem 2rem", borderBottom: "1px solid #1f2937", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.85rem", color: "#a5b4fc" }}>Doctor Assistant</div>
        <div style={{ display: "flex", gap: "0.5rem", background: "#020617", padding: "0.25rem", borderRadius: "999px", border: "1px solid #1e293b" }}>
          <button onClick={() => setRole("patient")} style={{ borderRadius: "999px", border: "none", padding: "0.4rem 0.9rem", fontSize: "0.85rem", cursor: "pointer", background: role === "patient" ? "#1d4ed8" : "transparent", color: role === "patient" ? "#e5e7eb" : "#9ca3af" }}>
            Patient
          </button>
          <button onClick={() => setRole("doctor")} style={{ borderRadius: "999px", border: "none", padding: "0.4rem 0.9rem", fontSize: "0.85rem", cursor: "pointer", background: role === "doctor" ? "#1d4ed8" : "transparent", color: role === "doctor" ? "#e5e7eb" : "#9ca3af" }}>
            Doctor
          </button>
        </div>
      </header>
      <main style={{ flex: 1, display: "flex", justifyContent: "center", padding: "2rem" }}>{role === "patient" ? <PatientView /> : <DoctorView />}</main>
    </div>
  );
}


