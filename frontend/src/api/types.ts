export type Role = "student" | "counselor";
export type Dimension = "E" | "L" | "Q" | "D";
export type RiskLevel = "high" | "medium" | "low" | "unknown";
export type EvalStatus = "pass" | "fail" | "not_run";

export interface LoginRequest {
  role: Role;
  student_id?: string | null;
}

export interface LoginResponse {
  role: Role;
  student_id: string | null;
}

export interface StudentSummary {
  id: string;
  name: string;
  program: string;
  campus: string;
  career_track: string;
}

export interface Assessment {
  subskill: string;
  score: number;
  cycle: number;
}

export interface Student extends StudentSummary {
  days_to_placement: number;
  assessments: Assessment[];
  attendance_pct: Partial<Record<Dimension, number>>;
  time_on_task_hrs: Partial<Record<Dimension, number>>;
  recent_signals: string[];
}

export interface DimensionScore {
  dimension: Dimension;
  score: number;
  benchmark: number;
  assessment_avg: number;
  attendance_pct: number;
  time_on_task_hrs: number;
  signals: string[];
}

export interface ReadinessResult {
  student_id: string;
  track: string;
  overall: number;
  dimensions: DimensionScore[];
}

export interface ReadinessNarrative {
  student_id: string;
  text: string;
}

export interface Gap {
  subskill: string;
  dimension: Dimension;
  student_score: number;
  benchmark: number;
  gap_size: number;
  priority_score: number;
  rank: number;
  jd_frequency: number | null;
  signals: string[];
  rationale: string | null;
}

export interface AtRiskAssessment {
  student_id: string;
  risk_level: RiskLevel;
  flagged: boolean;
  readiness: number;
  trajectory_slope: number | null;
  days_to_placement: number;
  primary_gap: Gap | null;
  contributing_signals: string[];
}

export interface InterventionBrief {
  student_id: string;
  lines: string[];
  contributing_signals: string[];
}

export interface EvalCase {
  name: string;
  passed: boolean;
  expected: unknown;
  actual: unknown;
  note: string | null;
}

export interface EvalResult {
  name: string;
  status: EvalStatus;
  metrics: Record<string, number>;
  cases: EvalCase[];
}

export interface EvalsReport {
  status: EvalStatus;
  ran_at: string | null;
  suites: EvalResult[];
}
