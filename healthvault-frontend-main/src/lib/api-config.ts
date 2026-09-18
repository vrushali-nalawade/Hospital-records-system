/**
 * Centralized API Base URL Configuration for HealthVault Frontend.
 * In browser production, routes through Next.js proxy /api/backend to permanently eliminate CORS.
 */
export const API_BASE_URL =
  typeof window !== "undefined"
    ? "/api/backend"
    : process.env.NEXT_PUBLIC_API_URL || "https://hospital-records-system.onrender.com";

