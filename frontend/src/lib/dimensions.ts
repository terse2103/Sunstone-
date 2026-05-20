import type { Dimension } from "../api/types";

export const DIMENSION_ORDER: readonly Dimension[] = ["E", "L", "Q", "D"];

export const DIMENSION_LABEL: Record<Dimension, string> = {
  E: "English",
  L: "Logic",
  Q: "Quant",
  D: "Domain",
};

export function formatSubskill(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function riskBand(score: number): "high" | "medium" | "low" {
  if (score < 55) return "high";
  if (score < 70) return "medium";
  return "low";
}

export const RISK_BAND_STYLE: Record<"high" | "medium" | "low", string> = {
  high: "bg-danger-500/10 text-danger-500 border-danger-500/40",
  medium: "bg-warning-500/10 text-warning-500 border-warning-500/40",
  low: "bg-success-500/10 text-success-500 border-success-500/40",
};

export const RISK_BAND_LABEL: Record<"high" | "medium" | "low", string> = {
  high: "At risk",
  medium: "Borderline",
  low: "On track",
};
