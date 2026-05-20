import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { ReadinessNarrative } from "../components/ReadinessNarrative";
import { ReadinessScoreCard } from "../components/ReadinessScoreCard";
import { SkillRadarChart } from "../components/SkillRadarChart";
import { TopGapsList } from "../components/TopGapsList";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import NotFound from "./NotFound";

export default function StudentDashboard() {
  const { id = "" } = useParams<{ id: string }>();

  const studentQ = useQuery({
    queryKey: ["student", id],
    queryFn: () => api.getStudent(id),
    enabled: !!id,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return failureCount < 1;
    },
  });

  const readinessQ = useQuery({
    queryKey: ["readiness", id],
    queryFn: () => api.getReadiness(id),
    enabled: !!id,
  });

  const gapsQ = useQuery({
    queryKey: ["gaps", id],
    queryFn: () => api.getGaps(id, 3),
    enabled: !!id,
  });

  const narrativeQ = useQuery({
    queryKey: ["narrative", id],
    queryFn: () => api.getNarrative(id),
    enabled: !!id,
  });

  if (studentQ.isError && studentQ.error instanceof ApiError && studentQ.error.status === 404) {
    return <NotFound />;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-brand-700">
            Student dashboard
          </p>
          {studentQ.data ? (
            <h1 className="text-2xl font-semibold text-ink-900 md:text-3xl">
              {studentQ.data.name}
            </h1>
          ) : (
            <Skeleton className="mt-1 h-8 w-48" />
          )}
          {studentQ.data ? (
            <p className="text-sm text-ink-600">
              {studentQ.data.program} · {studentQ.data.campus} · {studentQ.data.career_track}
            </p>
          ) : (
            <Skeleton className="mt-2 h-4 w-64" />
          )}
        </div>
      </header>

      {narrativeQ.isError ? null : (
        <ReadinessNarrative
          narrative={narrativeQ.data}
          loading={narrativeQ.isLoading}
        />
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <section aria-labelledby="readiness-h">
          <h2 id="readiness-h" className="sr-only">
            Readiness score
          </h2>
          {readinessQ.isLoading ? (
            <CardSkeleton lines={5} />
          ) : readinessQ.isError ? (
            <ErrorState
              title="Couldn’t load readiness"
              message={
                readinessQ.error instanceof ApiError
                  ? readinessQ.error.message
                  : "Network error reaching the backend."
              }
              onRetry={() => readinessQ.refetch()}
            />
          ) : readinessQ.data ? (
            <ReadinessScoreCard readiness={readinessQ.data} />
          ) : null}
        </section>

        <section aria-labelledby="radar-h">
          <h2 id="radar-h" className="sr-only">
            Skill radar
          </h2>
          {readinessQ.isLoading ? (
            <CardSkeleton lines={6} />
          ) : readinessQ.data ? (
            <SkillRadarChart readiness={readinessQ.data} />
          ) : null}
        </section>
      </div>

      <section aria-labelledby="gaps-h">
        <h2 id="gaps-h" className="sr-only">
          Top priority gaps
        </h2>
        {gapsQ.isError ? (
          <ErrorState
            title="Couldn’t load priority gaps"
            message={
              gapsQ.error instanceof ApiError
                ? gapsQ.error.message
                : "Network error reaching the backend."
            }
            onRetry={() => gapsQ.refetch()}
          />
        ) : (
          <TopGapsList gaps={gapsQ.data ?? []} loading={gapsQ.isLoading} />
        )}
      </section>
    </div>
  );
}

function CardSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <div className="rounded-2xl border border-ink-200 bg-white p-5 shadow-sm md:p-6">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="mt-3 h-10 w-2/3" />
      <div className="mt-4 space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-full" />
        ))}
      </div>
    </div>
  );
}
