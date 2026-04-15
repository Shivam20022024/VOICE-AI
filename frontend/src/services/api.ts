
// src/services/api.ts
// Centralized API wrapper for your FastAPI backend

import { APIAnalysisResponse, CallFromAPI } from "../types";

/**
 * Backend URL (Vite environment variable recommended)
 * Add this to `.env.local`:
 * VITE_API_URL=http://localhost:8000
 */
const BASE =
  (import.meta.env as any).VITE_API_URL || "http://localhost:8000";

/**
 * Helper: Parse JSON or throw a readable error
 */
async function handleJSON(res: Response) {
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ---------------- Existing methods ----------------

  /**
   * GET all calls
   */
  getAllCalls: async (
    limit = 200,
    skip = 0
  ): Promise<CallFromAPI[]> => {
    const res = await fetch(`${BASE}/calls?limit=${limit}&skip=${skip}`);
    return handleJSON(res);
  },

  /**
   * GET single call by ID
   */
  getCallById: async (callId: string): Promise<CallFromAPI> => {
    const res = await fetch(`${BASE}/calls/${encodeURIComponent(callId)}`);
    return handleJSON(res);
  },

  /**
   * Upload audio → triggers AI processing
   */
  uploadAudio: async (file: File): Promise<APIAnalysisResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE}/process-audio`, {
      method: "POST",
      body: formData,
    });

    return handleJSON(res);
  },

  /**
   * Optional backend ping
   */
  ping: async () => {
    const res = await fetch(`${BASE}/test-mongo`);
    return handleJSON(res);
  },

  // ---------------- ✅ EXCEL DOWNLOADS ----------------

  /**
   * Download overall calls Excel
   */
  downloadOverallExcel: () => {
    window.open(`${BASE}/download/overall`, "_blank");
  },

  /**
   * Download weekly calls Excel
   */
  downloadWeeklyCallsExcel: () => {
    window.open(`${BASE}/download/weekly-calls`, "_blank");
  },

  /**
   * Download weekly sales Excel
   */
  downloadWeeklySalesExcel: () => {
    window.open(`${BASE}/download/weekly-sales`, "_blank");
  },
};
