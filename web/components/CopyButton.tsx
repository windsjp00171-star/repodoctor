"use client";
import { useState } from "react";
import { copy } from "@/lib/copy";
import { motion } from "@/lib/motion";

export function CopyButton({ text, label = copy.report.copy, className = "" }: { text: string; label?: string; className?: string }) {
  const [state, setState] = useState<"idle" | "done" | "fallback">("idle");
  const onClick = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setState("done");
    } catch {
      setState("fallback");
    }
    setTimeout(() => setState("idle"), motion.copiedMs);
  };
  return (
    <button type="button" onClick={onClick}
      className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition ${state === "done" ? "scale-105 border-healthy text-healthy" : "border-primary text-primary hover:bg-primary/10"} ${className}`}>
      {state === "done" ? `✓ ${copy.report.copied}` : state === "fallback" ? copy.report.copyFallback : label}
    </button>
  );
}
