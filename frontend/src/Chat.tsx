import { FormEvent, useEffect, useRef, useState, useCallback } from "react";
import { authFetch } from "./api";
import { useAuth } from "./AuthContext";

type Message = {
  id: string;
  sender: "user" | "assistant" | "system";
  content: string;
};

type ChatProps = {
  endpoint: string;
  placeholder: string;
  /** When this changes to a non-empty value, it replaces the current input text
   * (used by "Book" on the Find a Doctor view to jump into Chat pre-filled). */
  prefill?: string;
};

export function Chat({ endpoint, placeholder, prefill }: ChatProps) {
  const { token } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (prefill) setInput(prefill);
  }, [prefill]);

  const sendMessageToBackend = useCallback(
    async (content: string) => {
      const res = await authFetch(endpoint, token, {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          message: content
        })
      });

      if (!res.ok) {
        throw new Error("Backend error");
      }
      return res.json();
    },
    [endpoint, sessionId, token]
  );

  async function send(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
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
    <div className="dash-chat-panel">
      <div className="dash-chat-msgs">
        {messages.map(m => (
          <div key={m.id} style={{ display: "flex", justifyContent: m.sender === "user" ? "flex-end" : "flex-start" }}>
            <div className={`dash-bubble ${m.sender === "user" ? "user" : m.sender === "assistant" ? "agent" : "system"}`}>
              {m.content}
            </div>
          </div>
        ))}

        {loading && <div className="dash-chat-loading">Thinking{"…"}</div>}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send} className="dash-chat-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={loading}
        />
        <button type="submit" className="dash-send-btn" disabled={loading}>
          {loading ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}
