import { request } from "./client";
import type {
  AtRiskAssessment,
  EvalsReport,
  Gap,
  InterventionBrief,
  LoginRequest,
  LoginResponse,
  ReadinessNarrative,
  ReadinessResult,
  Student,
  StudentSummary,
} from "./types";

export const api = {
  login(payload: LoginRequest) {
    return request<LoginResponse>("/api/auth/login", { method: "POST", body: payload });
  },

  listStudents() {
    return request<StudentSummary[]>("/api/students");
  },

  getStudent(id: string) {
    return request<Student>(`/api/students/${encodeURIComponent(id)}`);
  },

  getReadiness(id: string) {
    return request<ReadinessResult>(`/api/students/${encodeURIComponent(id)}/readiness`);
  },

  getNarrative(id: string) {
    return request<ReadinessNarrative>(
      `/api/students/${encodeURIComponent(id)}/narrative`,
    );
  },

  getGaps(id: string, n = 3) {
    return request<Gap[]>(`/api/students/${encodeURIComponent(id)}/gaps?n=${n}`);
  },

  atRiskStudents() {
    return request<AtRiskAssessment[]>("/api/counselor/at-risk");
  },

  interventionBrief(id: string) {
    return request<InterventionBrief>(
      `/api/counselor/students/${encodeURIComponent(id)}/brief`,
    );
  },

  markAction(id: string) {
    return request<void>(
      `/api/counselor/students/${encodeURIComponent(id)}/action`,
      { method: "POST" },
    );
  },

  evalsReport() {
    return request<EvalsReport>("/api/evals/results");
  },
};
