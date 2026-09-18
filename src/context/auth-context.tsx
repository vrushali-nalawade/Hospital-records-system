"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getDemoSession, logout as logoutService } from "@/lib/services/auth-service";
import { auth } from "@/lib/firebase/config";
import { onAuthStateChanged } from "firebase/auth";
import type { AppUser } from "@/types";

interface AuthContextValue {
  user: AppUser | null;
  loading: boolean;
  setUser: (u: AppUser | null) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  const setUser = (u: AppUser | null) => {
    setUserState(u);
    if (typeof window !== "undefined" && u) {
      try {
        localStorage.setItem(`hrl_profile_${u.uid}`, JSON.stringify(u));
        if (u.email) {
          localStorage.setItem(`hrl_profile_${u.email.toLowerCase()}`, JSON.stringify(u));
        }
        const session = localStorage.getItem("hrl_demo_session");
        if (session) {
          const parsed = JSON.parse(session);
          localStorage.setItem("hrl_demo_session", JSON.stringify({ ...parsed, ...u }));
        }
      } catch (e) {
        console.error("Error saving user profile locally:", e);
      }
    }
  };

  useEffect(() => {
    const getSavedProfile = (uid: string, email?: string): Partial<AppUser> | null => {
      if (typeof window === "undefined") return null;
      try {
        const byUid = localStorage.getItem(`hrl_profile_${uid}`);
        if (byUid) return JSON.parse(byUid);
        if (email) {
          const byEmail = localStorage.getItem(`hrl_profile_${email.toLowerCase()}`);
          if (byEmail) return JSON.parse(byEmail);
        }
      } catch (e) {
        console.error(e);
      }
      return null;
    };

    // Initial load from session storage
    const initialUser = getDemoSession();
    if (initialUser) {
      const saved = getSavedProfile(initialUser.uid, initialUser.email);
      setUserState(saved ? { ...initialUser, ...saved } as AppUser : initialUser);
    }

    // Sync with Firebase Auth state if configured
    if (auth) {
      const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
        if (firebaseUser) {
          const email = firebaseUser.email || "";
          const saved = getSavedProfile(firebaseUser.uid, email);
          const currentSession = getDemoSession();

          const isDoctor =
            email.endsWith("@hospital.org") ||
            email.endsWith("@demo.health") ||
            email.endsWith("@healthvault.com") ||
            email.endsWith("@doctor.com");

          let resolvedUser: AppUser;

          if (currentSession && (currentSession.uid === firebaseUser.uid || currentSession.email === email)) {
            resolvedUser = { ...currentSession, ...(saved || {}) } as AppUser;
          } else {
            resolvedUser = isDoctor
              ? {
                  uid: firebaseUser.uid,
                  email: email,
                  fullName: saved?.fullName || firebaseUser.displayName || "Doctor",
                  role: "doctor",
                  createdAt: saved?.createdAt || new Date().toISOString(),
                }
              : {
                  uid: firebaseUser.uid,
                  email: email,
                  fullName: saved?.fullName || firebaseUser.displayName || "Patient",
                  role: "patient",
                  phone: saved?.phone || "+91 98765 43210",
                  dateOfBirth: saved?.dateOfBirth || "1995-05-15",
                  gender: (saved?.gender as any) || "other",
                  createdAt: saved?.createdAt || new Date().toISOString(),
                };
          }
          setUserState(resolvedUser);
        }
        setLoading(false);
      });
      return () => unsubscribe();
    } else {
      setLoading(false);
    }
  }, []);

  const logout = async () => {
    await logoutService();
    setUserState(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
