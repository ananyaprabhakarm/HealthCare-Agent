import { useState } from "react";
import { Chat } from "./Chat";

type Summary = {
  doctor_name: string;
  timeframe: string;
  stats: { total: number; by_status: Record<string, number> };
  summary: string;
};

export function DoctorView() {
  const [email, setEmail] = useState("ahuja@example.com");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);

  async function requestSummary(timeframe: string) {
    setLoading(true);
    try {
      const res = await fetch("/api/doctor/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doctor_email: email, timeframe })
      });
      const data = await res.json();
      setSummary(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ width: "100%", display: "grid", gridTemplateColumns: "minmax(0,2fr) minmax(0,1.3fr)", gap: "1.75rem" }}>
      <div>
        <div style={{ marginBottom: "0.5rem" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 600, color: "#e5e7eb" }}>Doctor assistant</div>
          <div style={{ fontSize: "0.9rem", color: "#9ca3af", marginTop: "0.25rem" }}>Ask for stats in natural language or use the quick summary panel.</div>
        </div>
        <Chat endpoint="/api/chat/doctor" placeholder='e.g. "How many appointments do I have today and tomorrow?"' userEmail={email} />
      </div>
      <div style={{ alignSelf: "stretch", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ padding: "1rem 1.25rem", borderRadius: "1.25rem", border: "1px solid #1f2937", background: "linear-gradient(145deg,rgba(56,189,248,0.15),rgba(129,140,248,0.05))" }}>
          <div style={{ fontSize: "0.8rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#a5b4fc", marginBottom: "0.75rem" }}>Summary controls</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <label style={{ fontSize: "0.85rem", color: "#e5e7eb" }}>
              Notification email
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                style={{ marginTop: "0.35rem", width: "100%", padding: "0.5rem 0.75rem", borderRadius: "0.75rem", border: "1px solid #1f2937", background: "#020617", color: "#e5e7eb", fontSize: "0.85rem" }}
              />
            </label>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
              <button
                onClick={() => requestSummary("yesterday")}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "0.55rem 0.75rem",
                  borderRadius: "999px",
                  border: "none",
                  fontSize: "0.85rem",
                  cursor: loading ? "default" : "pointer",
                  background: "#0f172a",
                  color: "#e5e7eb",
                  borderColor: "#1f2937",
                  borderStyle: "solid",
                  borderWidth: 1
                }}
              >
                Yesterday
              </button>
              <button
                onClick={() => requestSummary("today")}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "0.55rem 0.75rem",
                  borderRadius: "999px",
                  border: "none",
                  fontSize: "0.85rem",
                  cursor: loading ? "default" : "pointer",
                  background: "#1d4ed8",
                  color: "#e5e7eb",
                  boxShadow: "0 16px 40px rgba(37,99,235,0.4)"
                }}
              >
                Today
              </button>
              <button
                onClick={() => requestSummary("tomorrow")}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "0.55rem 0.75rem",
                  borderRadius: "999px",
                  border: "none",
                  fontSize: "0.85rem",
                  cursor: loading ? "default" : "pointer",
                  background: "#0f766e",
                  color: "#e5e7eb",
                  boxShadow: "0 16px 40px rgba(15,118,110,0.4)"
                }}
              >
                Tomorrow
              </button>
            </div>
            {loading && <div style={{ fontSize: "0.8rem", color: "#9ca3af" }}>Generating and dispatching summary via notification channel...</div>}
          </div>
        </div>
        {summary && (
          <div style={{ padding: "1rem 1.25rem", borderRadius: "1.25rem", border: "1px solid #1f2937", background: "#020617" }}>
            <div style={{ fontSize: "0.85rem", color: "#9ca3af", marginBottom: "0.25rem" }}>Latest generated summary</div>
            <div style={{ fontSize: "1rem", fontWeight: 600, color: "#e5e7eb" }}>{summary.summary}</div>
            <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#9ca3af" }}>
              Total appointments: <span style={{ color: "#e5e7eb" }}>{summary.stats.total}</span>
            </div>
            <div style={{ marginTop: "0.25rem", fontSize: "0.8rem", color: "#6b7280", display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
              {Object.entries(summary.stats.by_status).map(([status, count]) => (
                <span key={status} style={{ padding: "0.25rem 0.6rem", borderRadius: "999px", border: "1px solid #1f2937", background: "#020617" }}>
                  {status}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


