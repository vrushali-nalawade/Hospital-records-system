"use client";

import { IS_DEMO_MODE, DEMO_CREDENTIALS } from "@/lib/demo-mode";
import { auth } from "@/lib/firebase/config";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
  updateProfile,
} from "firebase/auth";
import {
  MOCK_PATIENT,
  MOCK_DOCTOR,
  MOCK_PATIENTS,
} from "@/lib/mock/mock-data";
import type { AppUser, PatientProfile, DoctorProfile } from "@/types";
import { API_BASE_URL } from "@/lib/api-config";

const LOCAL_KEY = "hrl_demo_session";
const API_URL = API_BASE_URL;

export const DISALLOWED_DOCTOR_DOMAINS = [
  "gmail.com",
  "yahoo.com",
  "hotmail.com",
  "outlook.com",
  "icloud.com",
  "aol.com",
  "protonmail.com",
];

export const ALLOWED_DOCTOR_DOMAINS = [
  "demo.health",
  "hospital.org",
  "healthvault.com",
  "doctor.com",
];

export interface RegisterPatientInput {
  fullName: string;
  email: string;
  password: string;
  phone: string;
  dateOfBirth: string;
  gender: "male" | "female" | "other";
}

export interface RegisterDoctorInput {
  fullName: string;
  email: string;
  password: string;
  specialization?: string;
  licenseId?: string;
}

export function validateDoctorEmailDomain(email: string): { valid: boolean; error?: string } {
  if (!email || !email.includes("@")) {
    return { valid: false, error: "Valid email address is required." };
  }
  const domain = email.split("@")[1]?.toLowerCase().trim() || "";
  if (DISALLOWED_DOCTOR_DOMAINS.includes(domain)) {
    return {
      valid: false,
      error: "Personal email accounts (Gmail, Yahoo, Hotmail, etc.) are prohibited for Doctor accounts. Professional doctor domain required (@hospital.org, @healthvault.com, @demo.health, @doctor.com).",
    };
  }
  const isAllowed =
    ALLOWED_DOCTOR_DOMAINS.includes(domain) ||
    domain.includes("hospital") ||
    domain.includes("health");
  if (!isAllowed) {
    return {
      valid: false,
      error: `Domain '@${domain}' is not recognized as an approved medical provider domain. Approved domains include: @hospital.org, @healthvault.com, @demo.health, @doctor.com`,
    };
  }
  return { valid: true };
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

export async function loginPatient(email: string, password: string): Promise<PatientProfile> {
  if (IS_DEMO_MODE) {
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
  
  if (!auth) {
    let user: PatientProfile;
    if (email === DEMO_CREDENTIALS.patient.email && password === DEMO_CREDENTIALS.patient.password) {
      user = MOCK_PATIENT;
    } else {
      const match = MOCK_PATIENTS.find((p) => p.email === email);
      user = match || {
        uid: "P001UID",
        email: email,
        fullName: email.split("@")[0].toUpperCase(),
        role: "patient",
        phone: "",
        dateOfBirth: "",
        gender: "other",
        createdAt: new Date().toISOString(),
      };
    }
    
    try {
      const token = `mock_token_${user.uid}_PATIENT_${user.email}`;
      const res = await fetch(`${API_URL}/patients/me`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${res.status}`);
      }
    } catch (e: any) {
      if (e?.message?.includes("Failed to fetch") || e?.message?.includes("NetworkError")) {
        console.warn("Backend unavailable during login, proceeding with session profile:", e);
      } else if (e?.message) {
        throw e;
      }
    }
    saveDemoSession(user);
    return user;
  }

  const cred = await signInWithEmailAndPassword(auth, email, password);
  const token = await cred.user.getIdToken();
  
  // Sync with backend profile
  try {
    await fetch(`${API_URL}/auth/me`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  } catch (e) {
    console.warn("Could not contact backend /auth/me during patient login:", e);
  }

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

export async function loginDoctor(email: string, password: string): Promise<DoctorProfile> {
  const domainValidation = validateDoctorEmailDomain(email);
  if (!domainValidation.valid) {
    throw new Error(domainValidation.error);
  }

  if (IS_DEMO_MODE) {
    if (
      email === DEMO_CREDENTIALS.doctor.email &&
      password === DEMO_CREDENTIALS.doctor.password
    ) {
      saveDemoSession(MOCK_DOCTOR);
      return MOCK_DOCTOR;
    }
    throw new Error("Invalid doctor credentials. Try the demo account shown below.");
  }
  
  if (!auth) {
    let user: DoctorProfile = {
      uid: "D001UID",
      email: email,
      fullName: "Dr. Doctor 1",
      role: "doctor",
      createdAt: new Date().toISOString(),
    };
    if (email === DEMO_CREDENTIALS.doctor.email && password === DEMO_CREDENTIALS.doctor.password) {
      user = MOCK_DOCTOR;
    } else if (email.includes("d002") || email.includes("doctor2")) {
      user = {
        uid: "D002UID",
        email: email,
        fullName: "Dr. Doctor 2",
        role: "doctor",
        createdAt: new Date().toISOString(),
      };
    }
    
    const token = `mock_token_${user.uid}_DOCTOR_${user.email}`;
    const res = await fetch(`${API_URL}/audit/me`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Doctor login unauthorized (Status ${res.status})`);
    }

    saveDemoSession(user);
    return user;
  }

  const cred = await signInWithEmailAndPassword(auth, email, password);
  const token = await cred.user.getIdToken();
  
  // Verify doctor authorization and auto-provision in PostgreSQL backend
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "Doctor login unauthorized by server policy.");
  }

  const cleanName = cred.user.displayName || `Dr. ${email.split("@")[0].charAt(0).toUpperCase() + email.split("@")[0].slice(1)}`;
  const user: DoctorProfile = {
    uid: cred.user.uid,
    email: cred.user.email ?? email,
    fullName: cleanName,
    role: "doctor",
    createdAt: new Date().toISOString(),
  };
  saveDemoSession(user);
  return user;
}

export async function registerDoctor(input: RegisterDoctorInput): Promise<DoctorProfile> {
  const domainValidation = validateDoctorEmailDomain(input.email);
  if (!domainValidation.valid) {
    throw new Error(domainValidation.error);
  }

  const cleanName = input.fullName.trim();
  const displayName = cleanName.startsWith("Dr.") ? cleanName : `Dr. ${cleanName}`;

  if (IS_DEMO_MODE) {
    const newDoctor: DoctorProfile = {
      uid: `doctor-${Date.now()}`,
      email: input.email,
      fullName: displayName,
      role: "doctor",
      specialization: input.specialization,
      licenseId: input.licenseId,
      createdAt: new Date().toISOString(),
    };
    saveDemoSession(newDoctor);
    return newDoctor;
  }

  if (!auth) {
    const newDoctor: DoctorProfile = {
      uid: `doctor-${Date.now()}`,
      email: input.email,
      fullName: displayName,
      role: "doctor",
      specialization: input.specialization,
      licenseId: input.licenseId,
      createdAt: new Date().toISOString(),
    };
    saveDemoSession(newDoctor);
    try {
      const token = `mock_token_${newDoctor.uid}_DOCTOR_${newDoctor.email}`;
      await fetch(`${API_URL}/doctor/register`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: displayName,
          specialty: input.specialization || null
        })
      });
    } catch (e) {
      console.error("Failed to provision doctor profile in dev backend:", e);
    }
    return newDoctor;
  }

  // 1. Create the Firebase Authentication account
  const cred = await createUserWithEmailAndPassword(
    auth,
    input.email,
    input.password
  );

  // 2. Update Firebase display name
  try {
    await updateProfile(cred.user, { displayName: displayName });
  } catch (e) {
    console.warn("Could not update Firebase profile displayName:", e);
  }

  // 3. Obtain the Firebase ID token
  const token = await cred.user.getIdToken();

  // 4. Send the authenticated token to the backend to create/provision Doctor profile in PostgreSQL
  try {
    const res = await fetch(`${API_URL}/doctor/register`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: displayName,
        specialty: input.specialization || null,
      }),
    });
    if (!res.ok) {
      // Fallback call to /auth/me which triggers get_current_user auto-provisioning
      await fetch(`${API_URL}/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
    }
  } catch (e) {
    console.error("Failed to provision doctor profile on backend:", e);
  }

  const newDoctor: DoctorProfile = {
    uid: cred.user.uid,
    email: input.email,
    fullName: displayName,
    role: "doctor",
    specialization: input.specialization,
    licenseId: input.licenseId,
    createdAt: new Date().toISOString(),
  };
  saveDemoSession(newDoctor);
  return newDoctor;
}

export async function registerPatient(input: RegisterPatientInput): Promise<PatientProfile> {
  if (IS_DEMO_MODE) {
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
  
  if (!auth) {
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
    try {
      const token = `mock_token_${newUser.uid}_PATIENT_${newUser.email}`;
      await fetch(`${API_URL}/patients/me`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
    } catch (e) {
      console.error("Failed to provision patient in live backend", e);
    }
    return newUser;
  }

  const cred = await createUserWithEmailAndPassword(
    auth,
    input.email,
    input.password
  );

  try {
    await updateProfile(cred.user, { displayName: input.fullName });
  } catch (e) {
    console.warn("Could not update Firebase displayName:", e);
  }

  const token = await cred.user.getIdToken();
  try {
    await fetch(`${API_URL}/auth/me`, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
  } catch (e) {
    console.error("Failed to auto-provision patient in backend:", e);
  }

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
    return { demo: true };
  }
  await sendPasswordResetEmail(auth, email);
  return { demo: false };
}
