import type {
  PatientProfile,
  DoctorProfile,
  MedicalRecord,
  Consent,
  AccessLog,
  TimelineEvent,
} from "@/types";

// NOTE: All data below is synthetic demo/mock data for presentation
// purposes only. No real patient information is used anywhere in this app.

export const MOCK_PATIENT: PatientProfile = {
  uid: "patient-demo-1",
  email: "patient@demo.health",
  fullName: "Aarav Sharma",
  role: "patient",
  phone: "+91 90000 00001",
  dateOfBirth: "1996-04-12",
  gender: "male",
  createdAt: "2026-01-10T09:00:00.000Z",
};

export const MOCK_DOCTOR: DoctorProfile = {
  uid: "doctor-demo-1",
  email: "doctor@demo.health",
  fullName: "Dr. Priya Verma",
  role: "doctor",
  specialization: "General Physician",
  licenseId: "MH-DEMO-4471",
  createdAt: "2025-11-02T09:00:00.000Z",
};

export const MOCK_DOCTORS: DoctorProfile[] = [
  MOCK_DOCTOR,
  {
    uid: "doctor-demo-2",
    email: "doctor2@demo.health",
    fullName: "Dr. Rohan Deshmukh",
    role: "doctor",
    specialization: "Cardiologist",
    licenseId: "MH-DEMO-5521",
    createdAt: "2025-09-14T09:00:00.000Z",
  },
];

export const MOCK_PATIENTS: PatientProfile[] = [
  MOCK_PATIENT,
  {
    uid: "patient-demo-2",
    email: "patient2@demo.health",
    fullName: "Sneha Kulkarni",
    role: "patient",
    phone: "+91 90000 00002",
    dateOfBirth: "1990-08-22",
    gender: "female",
    createdAt: "2026-02-01T09:00:00.000Z",
  },
  {
    uid: "patient-demo-3",
    email: "patient3@demo.health",
    fullName: "Vivaan Iyer",
    role: "patient",
    phone: "+91 90000 00003",
    dateOfBirth: "1985-01-30",
    gender: "male",
    createdAt: "2026-03-05T09:00:00.000Z",
  },
];

export const MOCK_RECORDS: MedicalRecord[] = [
  {
    recordId: "rec-1",
    patientId: "patient-demo-1",
    uploadedBy: "patient-demo-1",
    recordType: "blood_report",
    fileName: "blood_report_aug2026.pdf",
    fileUrl: "/demo-files/blood_report_aug2026.pdf",
    fileSizeKb: 812,
    mimeType: "application/pdf",
    processingStatus: "ready",
    isMockExtraction: true,
    extractedInformation: [
      { label: "Report Date", value: "10 August 2026" },
      { label: "Hemoglobin", value: "13.2 g/dL" },
      { label: "WBC", value: "7,200 /µL" },
      { label: "Platelets", value: "250,000 /µL" },
      { label: "Fasting Glucose", value: "94 mg/dL" },
    ],
    createdAt: "2026-08-10T07:20:00.000Z",
    updatedAt: "2026-08-10T07:22:00.000Z",
  },
  {
    recordId: "rec-2",
    patientId: "patient-demo-1",
    uploadedBy: "patient-demo-1",
    recordType: "prescription",
    fileName: "prescription_jul2026.jpg",
    fileUrl: "/demo-files/prescription_jul2026.jpg",
    fileSizeKb: 340,
    mimeType: "image/jpeg",
    processingStatus: "ready",
    isMockExtraction: true,
    extractedInformation: [
      { label: "Prescribed By", value: "Dr. Priya Verma" },
      { label: "Date", value: "22 July 2026" },
      { label: "Medication", value: "Amoxicillin 500mg, twice daily" },
      { label: "Duration", value: "5 days" },
    ],
    createdAt: "2026-07-22T11:00:00.000Z",
    updatedAt: "2026-07-22T11:02:00.000Z",
  },
  {
    recordId: "rec-3",
    patientId: "patient-demo-1",
    uploadedBy: "patient-demo-1",
    recordType: "discharge_summary",
    fileName: "discharge_summary_jun2026.pdf",
    fileUrl: "/demo-files/discharge_summary_jun2026.pdf",
    fileSizeKb: 1120,
    mimeType: "application/pdf",
    processingStatus: "ready",
    isMockExtraction: true,
    extractedInformation: [
      { label: "Admission Date", value: "12 June 2026" },
      { label: "Discharge Date", value: "15 June 2026" },
      { label: "Diagnosis (as recorded)", value: "Viral fever, resolved" },
      { label: "Attending Doctor", value: "Dr. Priya Verma" },
    ],
    createdAt: "2026-06-15T09:30:00.000Z",
    updatedAt: "2026-06-15T09:35:00.000Z",
  },
  {
    recordId: "rec-4",
    patientId: "patient-demo-1",
    uploadedBy: "patient-demo-1",
    recordType: "lab_report",
    fileName: "lipid_profile_may2026.pdf",
    fileUrl: "/demo-files/lipid_profile_may2026.pdf",
    fileSizeKb: 604,
    mimeType: "application/pdf",
    processingStatus: "ready",
    isMockExtraction: true,
    extractedInformation: [
      { label: "Report Date", value: "3 May 2026" },
      { label: "Total Cholesterol", value: "182 mg/dL" },
      { label: "LDL", value: "104 mg/dL" },
      { label: "HDL", value: "48 mg/dL" },
    ],
    createdAt: "2026-05-03T08:15:00.000Z",
    updatedAt: "2026-05-03T08:18:00.000Z",
  },
];

export const MOCK_TIMELINE: TimelineEvent[] = [
  {
    eventId: "tl-1",
    patientId: "patient-demo-1",
    date: "2026-08-10T07:20:00.000Z",
    recordType: "blood_report",
    title: "Blood Report Uploaded",
    summary: "Routine blood work including CBC and glucose panel.",
    recordId: "rec-1",
  },
  {
    eventId: "tl-2",
    patientId: "patient-demo-1",
    date: "2026-07-22T11:00:00.000Z",
    recordType: "prescription",
    title: "Prescription Uploaded",
    summary: "Prescribed antibiotics following a clinic visit.",
    recordId: "rec-2",
  },
  {
    eventId: "tl-3",
    patientId: "patient-demo-1",
    date: "2026-06-15T09:30:00.000Z",
    recordType: "visit",
    title: "Doctor Visit",
    summary: "Hospital admission for viral fever, discharged after 3 days.",
    recordId: "rec-3",
  },
  {
    eventId: "tl-4",
    patientId: "patient-demo-1",
    date: "2026-05-03T08:15:00.000Z",
    recordType: "lab_report",
    title: "Lab Report Uploaded",
    summary: "Lipid profile as part of an annual health checkup.",
    recordId: "rec-4",
  },
];

export const MOCK_CONSENTS: Consent[] = [
  {
    consentId: "cons-1",
    patientId: "patient-demo-1",
    doctorId: "doctor-demo-1",
    doctorName: "Dr. Priya Verma",
    status: "approved",
    permissions: ["blood_report", "prescription", "discharge_summary"],
    createdAt: "2026-06-14T10:00:00.000Z",
    expiresAt: "2026-12-14T10:00:00.000Z",
  },
  {
    consentId: "cons-2",
    patientId: "patient-demo-1",
    doctorId: "doctor-demo-2",
    doctorName: "Dr. Rohan Deshmukh",
    status: "pending",
    permissions: ["lab_report"],
    createdAt: "2026-08-09T09:00:00.000Z",
    expiresAt: null,
  },
];

export const MOCK_ACCESS_LOGS: AccessLog[] = [
  {
    logId: "log-1",
    patientId: "patient-demo-1",
    doctorId: "doctor-demo-1",
    doctorName: "Dr. Priya Verma",
    recordId: "rec-1",
    recordName: "blood_report_aug2026.pdf",
    action: "viewed",
    timestamp: "2026-08-10T12:00:00.000Z",
    consentStatus: "approved",
  },
  {
    logId: "log-2",
    patientId: "patient-demo-1",
    doctorId: "doctor-demo-1",
    doctorName: "Dr. Priya Verma",
    recordId: "rec-3",
    recordName: "discharge_summary_jun2026.pdf",
    action: "viewed",
    timestamp: "2026-06-16T08:00:00.000Z",
    consentStatus: "approved",
  },
  {
    logId: "log-3",
    patientId: "patient-demo-1",
    doctorId: "doctor-demo-2",
    doctorName: "Dr. Rohan Deshmukh",
    recordId: null,
    recordName: null,
    action: "requested_access",
    timestamp: "2026-08-09T09:00:00.000Z",
    consentStatus: "pending",
  },
];

export const recordTypeLabel: Record<string, string> = {
  prescription: "Prescription",
  blood_report: "Blood Report",
  lab_report: "Lab Report",
  medical_image: "Medical Image",
  doctor_note: "Doctor Note",
  discharge_summary: "Discharge Summary",
  visit: "Doctor Visit",
};
