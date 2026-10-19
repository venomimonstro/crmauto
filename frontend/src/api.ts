export type Organization = { id: string; name: string; role: string };
export type SessionUser = { id: string; email: string; organizations: Organization[] };
export type Customer = {
  id: string; kind: "person" | "company"; name: string; phone: string; email: string;
  notes: string; version: number; created_at: string;
};
export type Vehicle = {
  id: string; vin: string; plate: string; make: string; model: string;
  year: number | null; current_owner: string | null; version: number; created_at: string;
};
export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); }
}
let csrfToken = "";
export async function refreshCsrf(): Promise<void> {
  const response = await fetch("/api/v1/auth/csrf", { credentials: "same-origin" });
  if (!response.ok) throw new ApiError(response.status, "Не удалось установить защищённую сессию.");
  const data: { csrf_token: string } = await response.json();
  csrfToken = data.csrf_token;
}
export async function api<T>(
  path: string, options: { method?: "GET" | "POST" | "PATCH"; data?: unknown; organization?: string;
    idempotencyKey?: string; ifMatch?: number } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  if (method !== "GET" && !csrfToken) await refreshCsrf();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.organization) headers["X-Organization-ID"] = options.organization;
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken;
  }
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;
  if (options.ifMatch !== undefined) headers["If-Match"] = String(options.ifMatch);
  let response: Response;
  try {
    response = await fetch("/api/v1/" + path, {
      method, headers, body: options.data === undefined ? undefined : JSON.stringify(options.data),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "Не удалось подключиться к серверу. Проверьте соединение и повторите.");
  }
  // Django rotates CSRF secrets on login/logout. Force a fresh token for
  // the next mutation; otherwise the first action after login can get 403.
  if (response.ok && method === "POST" &&
      (path === "auth/login" || path === "auth/logout")) csrfToken = "";
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    let message = "Ошибка запроса. Повторите попытку.";
    if (payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
      if (typeof p.message_ru === "string") message = p.message_ru;
      else if (typeof p.detail === "string") message = p.detail;
    }
    throw new ApiError(response.status, message);
  }
  return payload as T;
}
