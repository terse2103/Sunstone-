import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import { EvalsResultsViewer } from "../components/EvalsResultsViewer";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";

export default function EvalsPage() {
  const reportQ = useQuery({
    queryKey: ["evals"],
    queryFn: () => api.evalsReport(),
  });

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-wide text-brand-700">
          Quality
        </p>
        <h1 className="text-2xl font-semibold text-ink-900 md:text-3xl">
          Evals
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Score calibration · Gap relevance · Early warning.
        </p>
      </header>

      {reportQ.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-32" />
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : reportQ.isError ? (
        <ErrorState
          title="Couldn’t load eval results"
          message={
            reportQ.error instanceof ApiError
              ? reportQ.error.message
              : "Network error reaching the backend."
          }
          onRetry={() => reportQ.refetch()}
        />
      ) : reportQ.data ? (
        <EvalsResultsViewer report={reportQ.data} />
      ) : null}
    </div>
  );
}
