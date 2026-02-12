import { FormEvent, useEffect, useRef, useState, useCallback } from "react";

type Message = {
  id: string;
  sender: "user" | "assistant" | "system";
  content: string;
};

type ChatProps = {
  endpoint: string;
  placeholder: string;
  userEmail?: string;
};

export function Chat({ endpoint, placeholder, userEmail }: ChatProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessageToBackend = useCallback(
    async (content: string) => {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: content,
          user_email: userEmail
        })
      });

      if (!res.ok) {
        throw new Error("Backend error");
      }
      return res.json();
    },
    [endpoint, sessionId, userEmail]
  );

  async function send(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const optimisticMessage: Message = {
      id: crypto.randomUUID(),
      sender: "user",
      content: trimmed
    };
    setMessages(prev => [...prev, optimisticMessage]);
    setLoading(true);

    try {
      const data = await sendMessageToBackend(trimmed);

      setSessionId(data.session_id || null);
      setMessages(
        data.messages.map((m: any) => ({
          id: m.id ?? crypto.randomUUID(),
          sender: m.sender,
          content: m.content
        }))
      );
      setInput("");
    } catch (err) {
      console.error(err);
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: "system",
          content: "Something went wrong. Please try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        maxWidth: "960px",
        height: "70vh",
        borderRadius: "2.5rem",
        border: "1px solid #1f2937",
        background:
          "radial-gradient(circle at top, rgba(59,130,246,0.15), transparent 55%), #020617",
        overflow: "hidden",
        boxShadow: "0 24px 80px rgba(15,23,42,0.75)"
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "1.25rem 1.5rem",
          borderBottom: "1px solid #111827",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <div style={{ fontSize: "0.9rem", color: "#9ca3af" }}>
          LLM-powered assistant with MCP-backed tools
        </div>

        <div style={{ display: "flex", gap: "0.4rem", fontSize: "0.75rem", color: "#6b7280" }}>
          {["FastAPI", "PostgreSQL", "MCP"].map(tag => (
            <span
              key={tag}
              style={{
                padding: "0.2rem 0.5rem",
                borderRadius: "999px",
                background: "#020617",
                border: "1px solid #1e293b"
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          padding: "1rem 1.5rem",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem"
        }}
      >
        {messages.map(m => (
          <div key={m.id} style={{ display: "flex", justifyContent: m.sender === "user" ? "flex-end" : "flex-start" }}>
            <div
              style={{
                maxWidth: "70%",
                padding: "0.7rem 1rem",
                borderRadius: "1.2rem",
                fontSize: "0.9rem",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                background:
                  m.sender === "user"
                    ? "linear-gradient(135deg,#2563eb,#4f46e5)"
                    : m.sender === "assistant"
                    ? "rgba(15,23,42,0.9)"
                    : "transparent",
                border: m.sender === "assistant" ? "1px solid #1f2937" : "none",
                color: m.sender === "user" ? "#e5e7eb" : "#d1d5db"
              }}
            >
              {m.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            Agent is thinking and possibly calling tools<span style={{ fontSize: "1.2em" }}>...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input box */}
      <form
        onSubmit={send}
        style={{
          padding: "1rem 1.5rem",
          borderTop: "1px solid #111827",
          display: "flex",
          gap: "0.75rem",
          alignItems: "center",
          background: "linear-gradient(to top,rgba(15,23,42,0.95),transparent)"
        }}
      >
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={placeholder}
          style={{
            flex: 1,
            background: "#020617",
            borderRadius: "999px",
            border: "1px solid #1f2937",
            padding: "0.7rem 1rem",
            fontSize: "0.9rem",
            color: "#e5e7eb"
          }}
        />

        <button
          type="submit"
          disabled={loading}
          style={{
            borderRadius: "999px",
            border: "none",
            padding: "0.7rem 1.4rem",
            background: loading ? "#4b5563" : "linear-gradient(135deg,#22c55e,#16a34a)",
            color: "#020617",
            fontSize: "0.9rem",
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            boxShadow: "0 12px 30px rgba(22,163,74,0.45)"
          }}
        >
          {loading ? "Running tools..." : "Send"}
        </button>
      </form>
    </div>
  );
}
