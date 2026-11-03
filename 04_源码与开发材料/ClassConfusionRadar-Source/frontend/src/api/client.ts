/**
 * 本文件的作用是：封装前端访问client后端接口的方法。
 */
function getDefaultApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  const isViteDevServer = window.location.port === "5173";
  if (isViteDevServer) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return window.location.origin;
}

const DEFAULT_API_BASE_URL = getDefaultApiBaseUrl();

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");

function buildApiBaseCandidates(): string[] {
  const candidates = new Set<string>([API_BASE_URL]);

  if (typeof window === "undefined") {
    candidates.add(DEFAULT_API_BASE_URL);
    return Array.from(candidates);
  }

  const isViteDevServer = window.location.port === "5173";
  const runtimeBase = isViteDevServer
    ? `${window.location.protocol}//${window.location.hostname}:8000`.replace(/\/$/, "")
    : window.location.origin.replace(/\/$/, "");
  candidates.add(runtimeBase);

  if (isViteDevServer && window.location.hostname === "127.0.0.1") {
    candidates.add(`${window.location.protocol}//localhost:8000`);
  }

  if (isViteDevServer && window.location.hostname === "localhost") {
    candidates.add(`${window.location.protocol}//127.0.0.1:8000`);
  }

  return Array.from(candidates);
}

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function extractErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "请求失败，请稍后重试。";
  }

  const detail = Reflect.get(payload, "detail");
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && typeof Reflect.get(item, "msg") === "string") {
          return String(Reflect.get(item, "msg"));
        }
        return "";
      })
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join("；");
    }
  }

  const message = Reflect.get(payload, "message");
  if (typeof message === "string") {
    return message;
  }

  return "请求失败，请稍后重试。";
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(extractErrorMessage(payload), response.status, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = {
    Accept: "application/json",
    ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...init?.headers,
  };

  let lastNetworkError: unknown = null;

  for (const baseUrl of buildApiBaseCandidates()) {
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        ...init,
        headers,
      });
      return await parseResponse<T>(response);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      lastNetworkError = error;
    }
  }

  throw new ApiError(
    "无法连接到后端服务，请确认 http://127.0.0.1:8000 已启动，然后刷新页面重试。",
    0,
    lastNetworkError,
  );
}

export { API_BASE_URL };
