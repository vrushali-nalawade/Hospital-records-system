/**
 * Centralized API Base URL Configuration for HealthVault Frontend.
 * LIVE API MODE uses NEXT_PUBLIC_API_URL or defaults to the Replit production backend.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";
