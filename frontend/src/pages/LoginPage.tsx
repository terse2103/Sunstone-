import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, API_BASE_URL, ApiError } from "../api";
import type { Role } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [role, setRole] = useState<Role>("student");
  const [studentId, setStudentId] = useState<string>("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const students = useQuery({
    queryKey: ["students"],
    queryFn: () => api.listStudents(),
    enabled: role === "student",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    if (role === "student" && !studentId) {
      setSubmitError("Please pick a student to continue.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.login({
        role,
        student_id: role === "student" ? studentId : null,
      });
      login({ role: res.role, studentId: res.student_id ?? null });
      navigate(res.role === "student" ? `/student/${res.student_id}` : "/counselor", {
        replace: true,
      });
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Login failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const studentsEmpty =
    role === "student" &&
    students.isSuccess &&
    students.data.length === 0;

  const studentsErrored = role === "student" && students.isError;

  return (
    <section className="mx-auto max-w-md">
      <div className="rounded-2xl border border-ink-200 bg-white p-6 shadow-sm md:p-8">
        <h1 className="text-2xl font-semibold text-ink-900 md:text-3xl">
          Sign in to PlacementIQ
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Mock auth — pick a role to explore the demo.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <fieldset>
            <legend className="text-sm font-medium text-ink-700">I am a</legend>
            <div
              role="radiogroup"
              className="mt-2 grid grid-cols-2 gap-2 rounded-lg bg-ink-100 p-1"
            >
              {(["student", "counselor"] as Role[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={role === r}
                  onClick={() => {
                    setRole(r);
                    setSubmitError(null);
                  }}
                  className={
                    "min-h-[44px] rounded-md px-3 py-2 text-sm font-medium capitalize transition-colors " +
                    (role === r
                      ? "bg-white text-ink-900 shadow"
                      : "text-ink-600 hover:text-ink-800")
                  }
                >
                  {r}
                </button>
              ))}
            </div>
          </fieldset>

          {role === "student" ? (
            <div>
              <label
                htmlFor="student-picker"
                className="block text-sm font-medium text-ink-700"
              >
                Pick a student
              </label>

              {students.isLoading ? (
                <Skeleton className="mt-2 h-11 w-full" label="Loading students" />
              ) : studentsErrored ? (
                <div className="mt-2">
                  <ErrorState
                    title="Couldn’t load students"
                    message={
                      students.error instanceof ApiError
                        ? students.error.message
                        : "Network error reaching the backend."
                    }
                    onRetry={() => students.refetch()}
                  />
                </div>
              ) : studentsEmpty ? (
                <div className="mt-2 rounded-lg border border-ink-200 bg-ink-50 p-3 text-sm text-ink-700">
                  <p>No students in the seed yet.</p>
                  <p className="mt-1 text-ink-600">
                    Check{" "}
                    <a
                      href={`${API_BASE_URL}/api/students`}
                      className="text-brand-700 underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {API_BASE_URL}/api/students
                    </a>{" "}
                    to debug.
                  </p>
                </div>
              ) : (
                <select
                  id="student-picker"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  className="mt-2 block min-h-[44px] w-full rounded-md border border-ink-300 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                >
                  <option value="">Select a student…</option>
                  {students.data?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} — {s.program} · {s.career_track}
                    </option>
                  ))}
                </select>
              )}
            </div>
          ) : (
            <p className="rounded-md bg-ink-50 px-3 py-2 text-sm text-ink-600">
              Counselors see every at-risk student across all tracks.
            </p>
          )}

          {submitError ? (
            <p role="alert" className="text-sm text-danger-500">
              {submitError}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={
              submitting ||
              (role === "student" && (studentsEmpty || studentsErrored || !studentId))
            }
            className="inline-flex min-h-[44px] w-full items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-300"
          >
            {submitting ? "Signing in…" : "Continue"}
          </button>
        </form>
      </div>
    </section>
  );
}
