import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth, Role } from "../AuthContext";
import { Logo } from "../Logo";
import "./marketing.css";

export function Signup() {
  const [searchParams] = useSearchParams();
  const initialRole = searchParams.get("role") === "doctor" ? "doctor" : "patient";
  const [role, setRole] = useState<Role>(initialRole);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { signup } = useAuth();
  const navigate = useNavigate();

  function switchRole(newRole: Role) {
    if (newRole === role) return;
    setRole(newRole);
    setName("");
    setEmail("");
    setPassword("");
    setPhone("");
    setSpecialization("");
    setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup({
        role,
        name,
        email,
        password,
        phone: role === "patient" ? phone || undefined : undefined,
        specialization: role === "doctor" ? specialization || undefined : undefined
      });
      navigate("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="marketing">
      <header>
        <Link to="/" className="logo">
          <Logo />
        </Link>
        <nav>
          <Link to="/login">Log in</Link>
        </nav>
      </header>

      <div className="auth-shell">
        <div className="auth-card">
          <h2>Create your account</h2>
          <div className="auth-subtitle">Book visits or check your schedule in plain language.</div>

          <div className="role-toggle">
            <button type="button" className={role === "patient" ? "active" : ""} onClick={() => switchRole("patient")}>
              I'm a patient
            </button>
            <button type="button" className={role === "doctor" ? "active" : ""} onClick={() => switchRole("doctor")}>
              I'm a doctor
            </button>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="signup-name">Full name</label>
              <input id="signup-name" value={name} onChange={e => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="signup-email">Email</label>
              <input id="signup-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="signup-password">Password</label>
              <input
                id="signup-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                minLength={6}
                required
              />
            </div>
            {role === "patient" && (
              <div className="field">
                <label htmlFor="signup-phone">Phone (optional)</label>
                <input id="signup-phone" value={phone} onChange={e => setPhone(e.target.value)} />
              </div>
            )}
            {role === "doctor" && (
              <div className="field">
                <label htmlFor="signup-specialization">Specialization (optional)</label>
                <input
                  id="signup-specialization"
                  value={specialization}
                  onChange={e => setSpecialization(e.target.value)}
                />
              </div>
            )}
            <button type="submit" className="auth-submit" disabled={loading}>
              {loading ? "Creating account..." : "Sign up"}
            </button>
          </form>

          <div className="auth-switch">
            Already have an account? <Link to="/login">Log in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
