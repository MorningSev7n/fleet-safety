"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

// shortcut: re-renders the server page on a timer; Phase 2 swaps this for Supabase Realtime.
export default function AutoRefresh({ seconds = 5 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => document.visibilityState === "visible" && router.refresh(), seconds * 1000);
    return () => clearInterval(id);
  }, [router, seconds]);
  return null;
}
