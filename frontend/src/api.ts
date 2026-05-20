import { AuthUser, QueryResponse, DocumentRecord, IngestionJob, ChatLog } from "./types";

export const AUTH_STORAGE_KEY = "legal-rag-auth-user";
const envGlobal = (window as any).ENV || {};
const API_BASE_URL = (envGlobal.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

const requestCache = new Map<string, { data: any; expiresAt: number }>();

export function clearApiCache() {
  requestCache.clear();
}

export function readStoredUser(): AuthUser | null {
  try {
    const value = window.localStorage.getItem(AUTH_STORAGE_KEY);
    return value ? (JSON.parse(value) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function readStoredToken(): string {
  return readStoredUser()?.token || "";
}

function resolveUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

type RequestOptions = RequestInit & { cacheTtl?: number };

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { cacheTtl, ...fetchInit } = init;
  const isCacheable = cacheTtl && cacheTtl > 0;
  let cacheKey = "";

  if (isCacheable) {
    const bodyStr = fetchInit.body instanceof FormData ? "" : String(fetchInit.body || "");
    cacheKey = `${fetchInit.method || "GET"}:${path}:${bodyStr}`;
    const cached = requestCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.data as T;
    }
  }

  const headers: Record<string, string> = fetchInit.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  if (fetchInit.headers) {
    Object.assign(headers, fetchInit.headers);
  }
  const token = readStoredToken();
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }
  
  const response = await fetch(resolveUrl(path), { ...fetchInit, headers });
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const parsed = JSON.parse(text) as { message?: string; error?: string };
      message = parsed.message || parsed.error || text;
    } catch {
      message = text;
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }
  
  const data = await response.json();
  if (isCacheable) {
    requestCache.set(cacheKey, { data, expiresAt: Date.now() + cacheTtl });
  }
  return data;
}

export const api = {
  async login(payload: { username: string; password: string }) {
    return request<AuthUser>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  async query(payload: { query: string; top_k: number; filters?: Record<string, string> }) {
    return request<QueryResponse>("/api/v1/rag/query", {
      method: "POST",
      body: JSON.stringify(payload),
      cacheTtl: 5 * 60 * 1000 // 5 minutes cache for same query
    });
  },
  async upload(file: File) {
    clearApiCache();
    const form = new FormData();
    form.append("file", file);
    return request<{ documentId: string; fileUrl: string; ingestionStatus: string }>("/api/v1/upload/files", {
      method: "POST",
      body: form,
      headers: {}
    });
  },
  async ingest(payload: { file_url: string; document_id?: string; document_type?: string; metadata?: Record<string, string> }) {
    clearApiCache();
    return request<{ task_id: string; status: string; message: string; document_id?: string; chunks_indexed: number }>(
      "/api/v1/ingest/",
      {
        method: "POST",
        body: JSON.stringify(payload)
      }
    );
  },
  async documents() {
    return request<{ documents: DocumentRecord[] }>("/api/v1/ingest/documents");
  },
  async jobs() {
    return request<{ jobs: IngestionJob[] }>("/api/v1/ingest/jobs");
  },
  async retry(taskId: string) {
    clearApiCache();
    return request(`/api/v1/ingest/jobs/${taskId}/retry`, { method: "POST" });
  },
  async disableDocument(documentId: string) {
    clearApiCache();
    return request(`/api/v1/ingest/documents/${documentId}/disable`, { method: "POST" });
  },
  async enableDocument(documentId: string) {
    clearApiCache();
    return request(`/api/v1/ingest/documents/${documentId}/enable`, { method: "POST" });
  },
  async ingestStats() {
    return request<{ documents_total: number; chunks_total: number; jobs_failed: number; jobs_processing: number }>(
      "/api/v1/ingest/admin/stats"
    );
  },
  async ragStats() {
    return request<{ chat_logs_total: number; low_confidence_total: number; reviewed_total: number }>(
      "/api/v1/admin/stats"
    );
  },
  async chatLogs() {
    return request<{ logs: ChatLog[] }>("/api/v1/admin/chat-logs", { cacheTtl: 15000 });
  },
  async reviewLog(id: string, review_status: string) {
    clearApiCache();
    return request(`/api/v1/admin/chat-logs/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ review_status })
    });
  }
};
