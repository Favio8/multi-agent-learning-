import type {
  AnswerPayload,
  AnswerResponse,
  BuildRequest,
  BuildResponse,
  CardsResponse,
  DocumentSummary,
  HealthResponse,
  IngestResponse,
  ProgressCollection,
  Report,
  ReviewPlan,
} from "@/types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  (import.meta.env.DEV ? "/api" : "http://127.0.0.1:8000");

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 30000) {
  let response: Response;
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    window.clearTimeout(timeoutHandle);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("请求超时，后端构建耗时过长或接口卡住了。", 408);
    }
    const message =
      error instanceof Error && error.message
        ? `无法连接后端服务：${error.message}`
        : "无法连接后端服务，请确认后端已经启动。";
    throw new ApiError(message, 0);
  }
  window.clearTimeout(timeoutHandle);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string; error?: string };
      message = payload.detail ?? payload.error ?? message;
    } catch {
      // Keep the default message.
    }

    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return request<HealthResponse>("/health");
}

export function listDocuments() {
  return request<DocumentSummary[]>("/documents");
}

export async function ingestDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: formData,
  }, 60000);
}

export function buildDocument(docId: string, payload?: BuildRequest) {
  return request<BuildResponse>(`/build/${docId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload ?? {}),
  }, 180000);
}

export function getCards(docId: string) {
  const query = new URLSearchParams({ doc_id: docId, limit: "200" });
  return request<CardsResponse>(`/cards?${query.toString()}`);
}

export function submitAnswer(payload: AnswerPayload) {
  return request<AnswerResponse>("/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getReviewPlan(userId: string) {
  const query = new URLSearchParams({ user_id: userId });
  return request<ReviewPlan>(`/review_plan?${query.toString()}`);
}

export function getReport(userId: string) {
  const query = new URLSearchParams({ user_id: userId });
  return request<Report>(`/report?${query.toString()}`);
}

export function saveProgress(payload: {
  user_id: string;
  doc_id: string;
  current_card_idx: number;
  total_cards: number;
}) {
  return request<{ status: string; message: string }>("/progress/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getAllProgress(userId: string) {
  return request<ProgressCollection>(`/progress/${userId}/all`);
}

export { API_BASE_URL, ApiError };
