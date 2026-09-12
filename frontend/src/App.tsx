import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { DoctorView } from "./DoctorView";
import { PatientView } from "./PatientView";

function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", fontFamily: "system-ui, sans-serif", background: "#0f172a", color: "#e5e7eb" }}>
      <header style={{ padding: "1rem 2rem", borderBottom: "1px solid #1f2937", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", rowGap: "0.5rem" }}>
        <div style={{ fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.85rem", color: "#a5b4fc" }}>Doctor Assistant</div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ fontSize: "0.85rem", color: "#9ca3af" }}>
            {user?.name} <span style={{ color: "#4b5563" }}>·</span> {user?.role}
          </div>
          <button
            onClick={logout}
            style={{ borderRadius: "999px", border: "1px solid #1f2937", padding: "0.4rem 0.9rem", fontSize: "0.85rem", cursor: "pointer", background: "transparent", color: "#e5e7eb" }}
          >
            Log out
          </button>
        </div>
      </header>
      <main style={{ flex: 1, display: "flex", justifyContent: "center", padding: "2rem" }}>
        {user?.role === "doctor" ? <DoctorView /> : <PatientView />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
