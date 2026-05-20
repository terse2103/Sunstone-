import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Role } from "../api/types";

export interface AuthUser {
  role: Role;
  studentId: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (user: AuthUser) => void;
  logout: () => void;
}

const STORAGE_KEY = "placementiq.auth";
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStored(): AuthUser | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AuthUser>;
    if (parsed.role !== "student" && parsed.role !== "counselor") return null;
    if (parsed.role === "student" && !parsed.studentId) return null;
    return { role: parsed.role, studentId: parsed.studentId ?? null };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStored());

  useEffect(() => {
    // Cross-tab + same-tab guard for EdgeCases §7.1 — if storage is cleared
    // elsewhere, drop the in-memory user so the next protected route bounces.
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) setUser(readStored());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const login = useCallback((next: AuthUser) => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setUser(next);
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, login, logout }),
    [user, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
