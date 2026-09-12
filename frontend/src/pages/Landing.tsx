import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./marketing.css";

const BUBBLES = [
  { id: "b1", role: "user", text: "I need to see Dr. Ahuja sometime tomorrow morning" },
  { id: "b2", role: "agent", text: "Dr. Ahuja has 9:30 AM and 11:00 AM open tomorrow. Which works?" },
  { id: "b3", role: "user", text: "9:30 works" },
  { id: "b4", role: "confirm", text: "Booked for 9:30 AM tomorrow. Confirmation sent to your email." },
] as const;

export function Landing() {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    const timers = BUBBLES.map((_, i) =>
      setTimeout(() => setVisibleCount(i + 1), 400 + i * 750)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="marketing">
      <header>
        <Link to="/" className="logo">
          health<span>care</span>.agent
        </Link>
        <nav>
          <Link to="/login">Log in</Link>
          <Link to="/signup" className="primary">Sign up</Link>
        </nav>
      </header>

      <section className="hero">
        <div>
          <h1>Book appointments the way you'd ask a friend.</h1>
          <p className="sub">
            No forms, no dropdowns, no calendar grids. Tell it what you need in
            plain language — it checks availability, books the slot, and
            confirms with your doctor.
          </p>
          <div className="cta-row">
            <Link to="/signup?role=patient" className="btn btn-patient">I'm a patient</Link>
            <Link to="/signup?role=doctor" className="btn btn-doctor">I'm a doctor</Link>
          </div>
        </div>

        <div className="chat-mock">
          <div className="tag">Patient · booking a visit</div>
          {BUBBLES.map((bubble, i) => (
            <div
              key={bubble.id}
              className={`bubble ${bubble.role} ${i < visibleCount ? "visible" : ""}`}
            >
              {bubble.text}
            </div>
          ))}
        </div>
      </section>

      <section className="split-section">
        <div className="label">
          One assistant, two very different jobs — built for the person actually using it.
        </div>
        <div className="split">
          <div className="panel patient">
            <div className="kicker">For patients</div>
            <h3>Say what you need, get a slot</h3>
            <p>Describe the visit in your own words. It finds real open times and confirms the booking on the spot.</p>
            <ul>
              <li>Check a doctor's open times</li>
              <li>Book, in one message</li>
              <li>Get an email + calendar invite</li>
            </ul>
          </div>
          <div className="panel doctor">
            <div className="kicker">For doctors</div>
            <h3>Ask about your day, not your dashboard</h3>
            <p>Get a straight answer about your schedule instead of digging through a table.</p>
            <ul>
              <li>"How many appointments today?"</li>
              <li>Instant summary by status</li>
              <li>Notified as bookings come in</li>
            </ul>
          </div>
        </div>
      </section>

      <footer>
        <div>healthcare.agent</div>
        <div>A conversational front door for appointment booking.</div>
      </footer>
    </div>
  );
}
