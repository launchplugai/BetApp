"use client";

import { useSyncExternalStore } from "react";

import {
  type DevMode,
  getDevSessionSnapshot,
  setStoredDevMode,
  subscribeToDevSession,
} from "@/lib/dev-session";

export function useDevSession() {
  return useSyncExternalStore(
    subscribeToDevSession,
    getDevSessionSnapshot,
    getDevSessionSnapshot,
  );
}

export function useDevMode() {
  const { mode } = useDevSession();

  function updateMode(nextMode: DevMode) {
    setStoredDevMode(nextMode);
  }

  return {
    mode,
    setMode: updateMode,
  };
}
