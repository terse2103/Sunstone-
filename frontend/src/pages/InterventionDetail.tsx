import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { InterventionBriefCard } from "../components/InterventionBriefCard";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import NotFound from "./NotFound";

export default function InterventionDetail() {
  const { id = "" } = useParams<{ id: string }>();

  const studentQ = useQuery({
    queryKey: ["student", id],
    queryFn: () => api.getStudent(id),
    enabled: !!id,
    retry: (failureCount, err) =>
      err instanceof ApiError && err.status === 404 ? false : failureCount < 1,
  });

  const briefQ = useQuery({
    queryKey: ["brief", id],
    queryFn: () => api.interventionBrief(id),
    enabled: !!id,
    retry: (failureCount, err) =>
      err instanceof ApiError && err.status === 404 ? false : failureCount < 1,
  });

  const atRiskListQ = useQuery({
    queryKey: ["at-risk"],
    queryFn: () => api.atRiskStudents(),
  });

  const assessment =
    atRiskListQ.data?.find((a) => a.student_id === id) ?? null;

  const fatal404 =
    (studentQ.error instanceof ApiError && studentQ.error.status === 404) ||
    (briefQ.error instanceof ApiError && briefQ.error.status === 404);
  if (fatal404) return <NotFound />;

  return (
    <div className="space-y-6">
      <Link
        to="/counselor"
        className="inline-flex items-center text-sm text-brand-700 hover:text-brand-800"
      >
        ← Back to at-risk list
      </Link>

      <header>
        <p className="text-xs font-medium uppercase tracking-wide text-brand-700">
          Intervention
        </p>
        {studentQ.data ? (
          <>
            <h1 className="text-2xl font-semibold text-ink-900 md:text-3xl break-words">
              {studentQ.data.name}
            </h1>
            <p className="text-sm text-ink-600">
              {studentQ.data.program} · {studentQ.data.campus} · {studentQ.data.career_track}
            </p>
          </>
        ) : (
          <>
            <Skeleton className="mt-1 h-8 w-56" />
            <Skeleton className="mt-2 h-4 w-72" />
          </>
        )}
      </header>

      {briefQ.isLoading ? (
        <div className="rounded-2xl border border-ink-200 bg-white p-5 md:p-6">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-4 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-5/6" />
          <Skeleton className="mt-2 h-4 w-3/4" />
          <Skeleton className="mt-6 h-11 w-40" />
        </div>
      ) : briefQ.isError ? (
        <ErrorState
          title="Couldn’t load the brief"
          message={
            briefQ.error instanceof ApiError
              ? briefQ.error.message
              : "Network error reaching the backend."
          }
          onRetry={() => briefQ.refetch()}
        />
      ) : briefQ.data ? (
        <InterventionBriefCard
          studentId={id}
          brief={briefQ.data}
          assessment={assessment}
        />
      ) : null}

      <p className="text-xs text-ink-500">
        Also see this student’s{" "}
        <Link to={`/student/${id}`} className="text-brand-700 underline">
          full dashboard
        </Link>
        .
      </p>
    </div>
  );
}
