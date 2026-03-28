const API_BASE_KEY = "betapp.apiBase";
const AUTH_TOKEN_KEY = "betapp.authToken";
const DEV_MODE_KEY = "betapp.devMode";
const BUILDER_HANDOFF_KEY = "betapp.builderHandoff";
const DEV_SESSION_EVENT = "betapp:dev-session";

export type DevMode = "live" | "mock";

const DEFAULT_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type DevSessionSnapshot = {
  apiBase: string;
  authToken: string;
  mode: DevMode;
};

const SERVER_SNAPSHOT: DevSessionSnapshot = {
  apiBase: DEFAULT_API_BASE_URL,
  authToken: "",
  mode: "live",
};

let lastSnapshot: DevSessionSnapshot | null = null;

function notifyDevSessionChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(DEV_SESSION_EVENT));
}

export function getStoredApiBaseUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_BASE_URL;
  return window.localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE_URL;
}

export function setStoredApiBaseUrl(value: string): void {
  if (typeof window === "undefined") return;
  const nextValue = value.trim() || DEFAULT_API_BASE_URL;
  window.localStorage.setItem(API_BASE_KEY, nextValue);
  notifyDevSessionChange();
}

export function getStoredAuthToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function setStoredAuthToken(value: string): void {
  if (typeof window === "undefined") return;
  const nextValue = value.trim();
  if (nextValue) window.localStorage.setItem(AUTH_TOKEN_KEY, nextValue);
  else window.localStorage.removeItem(AUTH_TOKEN_KEY);
  notifyDevSessionChange();
}

export function getStoredDevMode(): DevMode {
  if (typeof window === "undefined") return "live";
  const mode = window.localStorage.getItem(DEV_MODE_KEY);
  return mode === "mock" ? "mock" : "live";
}

export function setStoredDevMode(mode: DevMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DEV_MODE_KEY, mode);
  notifyDevSessionChange();
}

export function getStoredBuilderHandoff(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(BUILDER_HANDOFF_KEY) || "";
}

export function setStoredBuilderHandoff(value: string): void {
  if (typeof window === "undefined") return;
  const nextValue = value.trim();
  if (nextValue) window.localStorage.setItem(BUILDER_HANDOFF_KEY, nextValue);
  else window.localStorage.removeItem(BUILDER_HANDOFF_KEY);
  notifyDevSessionChange();
}

export function getDevSessionSnapshot(): DevSessionSnapshot {
  if (typeof window === "undefined") {
    return SERVER_SNAPSHOT;
  }

  const nextSnapshot = {
    apiBase: getStoredApiBaseUrl(),
    authToken: getStoredAuthToken(),
    mode: getStoredDevMode(),
  };

  if (
    lastSnapshot &&
    lastSnapshot.apiBase === nextSnapshot.apiBase &&
    lastSnapshot.authToken === nextSnapshot.authToken &&
    lastSnapshot.mode === nextSnapshot.mode
  ) {
    return lastSnapshot;
  }

  lastSnapshot = nextSnapshot;
  return nextSnapshot;
}


export function subscribeToDevSession(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};

  const handler = () => callback();
  window.addEventListener(DEV_SESSION_EVENT, handler);
  window.addEventListener("storage", handler);

  return () => {
    window.removeEventListener(DEV_SESSION_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}
