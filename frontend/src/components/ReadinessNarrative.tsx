import type { ReadinessNarrative as Narrative } from "../api/types";
import { Skeleton } from "./ui/Skeleton";

interface Props {
  narrative?: Narrative;
  loading?: boolean;
}

export function ReadinessNarrative({ narrative, loading }: Props) {
  return (
    <article
      aria-busy={loading || undefined}
      className="relative overflow-hidden rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-5 shadow-sm md:p-6"
    >
      <header className="flex items-center gap-2">
        <span className="inline-flex h-7 items-center gap-1 rounded-full bg-brand-600 px-2.5 text-[10px] font-semibold uppercase tracking-wide text-white">
          <SparkleIcon />
          AI summary
        </span>
        <span className="text-xs text-ink-500">
          Written by Claude from your scores · regenerates on data change
        </span>
      </header>

      {loading || !narrative ? (
        <div className="mt-3 space-y-2">
          <Skeleton className="h-4 w-full" label="Generating AI summary" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : (
        <p className="mt-3 text-base leading-relaxed text-ink-900 md:text-lg">
          {narrative.text}
        </p>
      )}
    </article>
  );
}

function SparkleIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M12 2 14 9l7 2-7 2-2 7-2-7-7-2 7-2z" />
    </svg>
  );
}
