// Determines whether the app runs against real Firebase or in DEMO MODE.
// DEMO MODE is automatically enabled when Firebase environment variables
// are not configured, so the full frontend can always be demonstrated.

export const isFirebaseConfigured = (): boolean => {
  return Boolean(
    process.env.NEXT_PUBLIC_FIREBASE_API_KEY &&
      process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID
  );
};

export const IS_DEMO_MODE = !isFirebaseConfigured();

export const DEMO_AI_DISCLAIMER =
  "AI-generated information is for record understanding only and is not medical advice.";

export const DEMO_CREDENTIALS = {
  patient: { email: "patient@demo.health", password: "Demo@1234" },
  doctor: { email: "doctor@demo.health", password: "Demo@1234" },
};
