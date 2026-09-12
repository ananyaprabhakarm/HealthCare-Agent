import { ReactNode, createContext, useContext, useEffect, useState } from "react";
import { apiUrl } from "./api";

export type Role = "patient" | "doctor";

export type User = {
  role: Role;
  name: string;
  email: string;
};

export type SignupPayload = {
  role: Role;
  name: string;
  email: string;
  password: string;
  phone?: string;
  specialization?: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_STORAGE_KEY = "hc_token";

async function parseJsonOrThrow(res: Response): Promise<any> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || "Something went wrong. Please try again.");
  }
  return data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(apiUrl("/api/auth/me"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("invalid session");
        const data = await res.json();
        if (!cancelled) setUser({ role: data.role, name: data.name, email: data.email });
      } catch {
        if (!cancelled) {
          setToken(null);
          setUser(null);
          try {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
          } catch {
            // ignore
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [token]);

  function persistToken(next: string) {
    setToken(next);
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, next);
    } catch {
      // ignore (e.g. private browsing storage restrictions)
    }
  }

  async function login(email: string, password: string) {
    const res = await fetch(apiUrl("/api/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await parseJsonOrThrow(res);
    persistToken(data.access_token);
    setUser({ role: data.role, name: data.name, email: data.email });
  }

  async function signup(payload: SignupPayload) {
    const res = await fetch(apiUrl("/api/auth/signup"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await parseJsonOrThrow(res);
    persistToken(data.access_token);
    setUser({ role: data.role, name: data.name, email: data.email });
  }

  function logout() {
    setToken(null);
    setUser(null);
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // ignore
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
