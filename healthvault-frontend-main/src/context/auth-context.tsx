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
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initial load from session storage
    const initialUser = getDemoSession();
    if (initialUser) {
      setUser(initialUser);
    }

    // Sync with Firebase Auth state if configured
    if (auth) {
      const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
        if (firebaseUser) {
          const currentSession = getDemoSession();
          if (currentSession && currentSession.uid === firebaseUser.uid) {
            setUser(currentSession);
          } else {
            const email = firebaseUser.email || "";
            const isDoctor =
              email.endsWith("@hospital.org") ||
              email.endsWith("@demo.health") ||
              email.endsWith("@healthvault.com") ||
              email.endsWith("@doctor.com");
            const syncedUser: AppUser = isDoctor
              ? {
                  uid: firebaseUser.uid,
                  email: email,
                  fullName: firebaseUser.displayName || "Doctor",
                  role: "doctor",
                  createdAt: new Date().toISOString(),
                }
              : {
                  uid: firebaseUser.uid,
                  email: email,
                  fullName: firebaseUser.displayName || "Patient",
                  role: "patient",
                  phone: "",
                  dateOfBirth: "",
                  gender: "other",
                  createdAt: new Date().toISOString(),
                };
            setUser(syncedUser);
          }
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
    setUser(null);
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
