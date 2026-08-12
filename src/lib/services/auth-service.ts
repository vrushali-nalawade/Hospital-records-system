"use client";

import { IS_DEMO_MODE, DEMO_CREDENTIALS } from "@/lib/demo-mode";
import { auth } from "@/lib/firebase/config";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
} from "firebase/auth";
import {
  MOCK_PATIENT,
  MOCK_DOCTOR,
  MOCK_PATIENTS,
} from "@/lib/mock/mock-data";
import type { AppUser, PatientProfile } from "@/types";

const LOCAL_KEY = "hrl_demo_session";

export interface RegisterPatientInput {
  fullName: string;
  email: string;
  password: string;
  phone: string;
  dateOfBirth: string;
  gender: "male" | "female" | "other";
}

function saveDemoSession(user: AppUser) {
  if (typeof window !== "undefined") {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(user));
  }
}

export function getDemoSession(): AppUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(LOCAL_KEY);
  return raw ? (JSON.parse(raw) as AppUser) : null;
}

export async function loginPatient(email: string, password: string) {
  if (IS_DEMO_MODE || !auth) {
    if (
      email === DEMO_CREDENTIALS.patient.email &&
      password === DEMO_CREDENTIALS.patient.password
    ) {
      saveDemoSession(MOCK_PATIENT);
      return MOCK_PATIENT;
    }
    const match = MOCK_PATIENTS.find((p) => p.email === email);
    if (match) {
      saveDemoSession(match);
      return match;
    }
    throw new Error(
      "Invalid credentials. Try the demo account shown below, or register a new patient."
    );
  }
  const cred = await signInWithEmailAndPassword(auth, email, password);
  const user: PatientProfile = {
    uid: cred.user.uid,
    email: cred.user.email ?? email,
    fullName: cred.user.displayName ?? "Patient",
    role: "patient",
    phone: "",
    dateOfBirth: "",
    gender: "other",
    createdAt: new Date().toISOString(),
  };
  saveDemoSession(user);
  return user;
}

export async function loginDoctor(email: string, password: string) {
  if (IS_DEMO_MODE || !auth) {
    if (
      email === DEMO_CREDENTIALS.doctor.email &&
      password === DEMO_CREDENTIALS.doctor.password
    ) {
      saveDemoSession(MOCK_DOCTOR);
      return MOCK_DOCTOR;
    }
    throw new Error("Invalid doctor credentials. Try the demo account shown below.");
  }
  const cred = await signInWithEmailAndPassword(auth, email, password);
  const user = {
    uid: cred.user.uid,
    email: cred.user.email ?? email,
    fullName: cred.user.displayName ?? "Doctor",
    role: "doctor" as const,
    createdAt: new Date().toISOString(),
  };
  saveDemoSession(user);
  return user;
}

export async function registerPatient(input: RegisterPatientInput) {
  if (IS_DEMO_MODE || !auth) {
    const newUser: PatientProfile = {
      uid: `patient-${Date.now()}`,
      email: input.email,
      fullName: input.fullName,
      role: "patient",
      phone: input.phone,
      dateOfBirth: input.dateOfBirth,
      gender: input.gender,
      createdAt: new Date().toISOString(),
    };
    saveDemoSession(newUser);
    return newUser;
  }
  const cred = await createUserWithEmailAndPassword(
    auth,
    input.email,
    input.password
  );
  const newUser: PatientProfile = {
    uid: cred.user.uid,
    email: input.email,
    fullName: input.fullName,
    role: "patient",
    phone: input.phone,
    dateOfBirth: input.dateOfBirth,
    gender: input.gender,
    createdAt: new Date().toISOString(),
  };
  saveDemoSession(newUser);
  return newUser;
}

export async function logout() {
  if (typeof window !== "undefined") localStorage.removeItem(LOCAL_KEY);
  if (auth) await firebaseSignOut(auth);
}

export async function forgotPassword(email: string) {
  if (IS_DEMO_MODE || !auth) {
    // Demo mode: simulate success without sending a real email.
    return { demo: true };
  }
  await sendPasswordResetEmail(auth, email);
  return { demo: false };
}
