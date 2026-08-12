// Core domain types for the Unified Digital Health Record Locker

export type UserRole = "patient" | "doctor";

export interface BaseUser {
  uid: string;
  email: string;
  fullName: string;
  role: UserRole;
  createdAt: string;
}

export interface PatientProfile extends BaseUser {
  role: "patient";
  phone: string;
  dateOfBirth: string;
  gender: "male" | "female" | "other";
}

export interface DoctorProfile extends BaseUser {
  role: "doctor";
  specialization?: string;
  licenseId?: string;
}

export type AppUser = PatientProfile | DoctorProfile;

export type RecordType =
  | "prescription"
  | "blood_report"
  | "lab_report"
  | "medical_image"
  | "doctor_note"
  | "discharge_summary";

export type ProcessingStatus =
  | "uploading"
  | "processing"
  | "ocr_completed"
  | "extracted"
  | "ready"
  | "failed";

export interface ExtractedField {
  label: string;
  value: string;
}

export interface MedicalRecord {
  recordId: string;
  patientId: string;
  uploadedBy: string;
  recordType: RecordType;
  fileName: string;
  fileUrl: string;
  fileSizeKb: number;
  mimeType: string;
  processingStatus: ProcessingStatus;
  extractedInformation: ExtractedField[];
  isMockExtraction: boolean;
  createdAt: string;
  updatedAt: string;
}

export type ConsentStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "revoked"
  | "expired";

export interface Consent {
  consentId: string;
  patientId: string;
  doctorId: string;
  doctorName: string;
  status: ConsentStatus;
  permissions: RecordType[];
  createdAt: string;
  expiresAt: string | null;
}

export type AccessAction = "viewed" | "downloaded" | "requested_access";

export interface AccessLog {
  logId: string;
  patientId: string;
  doctorId: string;
  doctorName: string;
  recordId: string | null;
  recordName: string | null;
  action: AccessAction;
  timestamp: string;
  consentStatus: ConsentStatus;
}

export interface TimelineEvent {
  eventId: string;
  patientId: string;
  date: string;
  recordType: RecordType | "visit";
  title: string;
  summary: string;
  recordId?: string;
}

export interface AIChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sourceRecordIds?: string[];
  timestamp: string;
}

export type Locale = "en" | "hi" | "mr";
