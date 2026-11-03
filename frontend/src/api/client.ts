/** fetch 封装：统一错误提示 */
import type { ReactNode } from 'react';

let errorNotifier: ((msg: ReactNode) => void) | null = null;
export function setErrorNotifier(fn: (msg: ReactNode) => void) {
  errorNotifier = fn;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, url: string, body?: unknown, isForm = false): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(url, {
      method,
      headers: body && !isForm ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? (isForm ? (body as FormData) : JSON.stringify(body)) : undefined,
    });
  } catch {
    errorNotifier?.('无法连接后端服务，请确认 FastAPI 已在 8000 端口启动');
    throw new ApiError(0, '网络错误');
  }
  const text = await resp.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* 非 JSON 响应 */
  }
  if (!resp.ok) {
    const msg =
      (data as { detail?: string } | null)?.detail ||
      (Array.isArray(data) && data[0]?.msg) ||
      `请求失败（${resp.status}）`;
    if (resp.status >= 500) errorNotifier?.(`服务异常：${msg}`);
    throw new ApiError(resp.status, String(msg));
  }
  return data as T;
}

export const http = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body),
  del: <T>(url: string) => request<T>('DELETE', url),
  upload: <T>(url: string, form: FormData) => request<T>('POST', url, form, true),
};

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : '';
}
