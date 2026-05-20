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
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-600 md:text-base">
          PlacementIQ makes calls that counselors and recruiters need to
          trust — readiness scores, top priority gaps, and at-risk flags.
          Each suite below runs the deterministic engine against
          hand-labelled <em>golden</em> student profiles whose correct
          answers we know, then checks the engine got them right.
        </p>
      </header>

      <section
        aria-labelledby="evals-how-heading"
        className="rounded-2xl border border-brand-200 bg-brand-50/60 p-4 md:p-5"
      >
        <h2
          id="evals-how-heading"
          className="text-sm font-semibold text-ink-900"
        >
          How this works
        </h2>
        <ul className="mt-2 space-y-1.5 text-sm text-ink-700">
          <li className="flex gap-2">
            <span aria-hidden className="select-none text-brand-500">•</span>
            <span>
              Three suites cover the three numerical decisions the engine
              makes: <strong>scoring</strong>, <strong>gap ranking</strong>,
              and <strong>at-risk flagging</strong>.
            </span>
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="select-none text-brand-500">•</span>
            <span>
              Each suite has an explicit pass threshold (shown beside its
              result). One failure flips the suite — and the overall
              report — to fail.
            </span>
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="select-none text-brand-500">•</span>
            <span>
              Only the deterministic math is tested. The LLM-written gap
              rationales and intervention briefs are{" "}
              <strong>excluded on purpose</strong> so results stay stable
              across model versions.
            </span>
          </li>
          <li className="flex gap-2">
            <span aria-hidden className="select-none text-brand-500">•</span>
            <span>
              The runner{" "}
              <code className="rounded bg-white/70 px-1.5 py-0.5 text-xs font-mono">
                python evals/run.py
              </code>{" "}
              re-executes every suite and writes{" "}
              <code className="rounded bg-white/70 px-1.5 py-0.5 text-xs font-mono">
                evals/results/report.json
              </code>
              ; this page reads that file live, so what you see is the
              latest committed run.
            </span>
          </li>
        </ul>
      </section>

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
