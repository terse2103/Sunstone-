import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { AtRiskTable } from "../components/AtRiskTable";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";

export default function CounselorDashboard() {
  const atRiskQ = useQuery({
    queryKey: ["at-risk"],
    queryFn: () => api.atRiskStudents(),
  });

  const studentsQ = useQuery({
    queryKey: ["students"],
    queryFn: () => api.listStudents(),
  });

  const { nameById, trackById } = useMemo(() => {
    const name: Record<string, string> = {};
    const track: Record<string, string> = {};
    for (const s of studentsQ.data ?? []) {
      name[s.id] = s.name;
      track[s.id] = s.career_track;
    }
    return { nameById: name, trackById: track };
  }, [studentsQ.data]);

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wide text-brand-700">
          Counselor
        </p>
        <h1 className="text-2xl font-semibold text-ink-900 md:text-3xl">
          At-risk students
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Flagged when readiness &lt; 55, trajectory ≤ 0, and ≥ 60 days to placement remain.
        </p>
      </header>

      {atRiskQ.isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : atRiskQ.isError ? (
        <ErrorState
          title="Couldn’t load at-risk students"
          message={
            atRiskQ.error instanceof ApiError
              ? atRiskQ.error.message
              : "Network error reaching the backend."
          }
          onRetry={() => atRiskQ.refetch()}
        />
      ) : (atRiskQ.data ?? []).length === 0 ? (
        <div className="rounded-2xl border border-success-500/30 bg-success-500/5 p-6 text-center">
          <p className="text-base font-medium text-success-500">
            All students currently on track.
          </p>
          <p className="mt-1 text-sm text-ink-600">
            No at-risk flags fire against the current seed.
          </p>
        </div>
      ) : (
        <AtRiskTable
          rows={atRiskQ.data ?? []}
          nameById={nameById}
          trackById={trackById}
        />
      )}
    </div>
  );
}
