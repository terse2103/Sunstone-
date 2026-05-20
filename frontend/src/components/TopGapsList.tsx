import type { Gap } from "../api/types";
import { DIMENSION_LABEL, formatSubskill } from "../lib/dimensions";
import { Skeleton } from "./ui/Skeleton";

interface Props {
  gaps: Gap[];
  loading?: boolean;
}

export function TopGapsList({ gaps, loading }: Props) {
  return (
    <article className="rounded-2xl border border-ink-200 bg-white p-5 shadow-sm md:p-6">
      <header className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wide text-ink-500">
          Top priority gaps
        </h2>
        <span className="text-xs text-ink-400">Ranked by gap × dimension weight</span>
      </header>

      {loading ? (
        <ul className="mt-4 space-y-3">
          {[0, 1, 2].map((i) => (
            <li key={i} className="rounded-xl border border-ink-200 p-4">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="mt-3 h-3 w-full" />
              <Skeleton className="mt-2 h-3 w-2/3" />
            </li>
          ))}
        </ul>
      ) : gaps.length === 0 ? (
        <p className="mt-4 rounded-lg bg-success-500/5 px-3 py-3 text-sm text-success-500">
          No priority gaps — on track across every benchmark.
        </p>
      ) : (
        <ol className="mt-4 space-y-3">
          {gaps.map((g) => (
            <GapRow key={`${g.rank}-${g.subskill}`} gap={g} />
          ))}
        </ol>
      )}
    </article>
  );
}

function GapRow({ gap }: { gap: Gap }) {
  return (
    <li className="rounded-xl border border-ink-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-ink-900">
          <span className="mr-2 text-ink-400">#{gap.rank}</span>
          {formatSubskill(gap.subskill)}
        </h3>
        <span className="inline-flex items-center rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
          {DIMENSION_LABEL[gap.dimension]}
        </span>
      </div>

      <p className="mt-1 text-xs text-ink-500">
        Score <span className="font-semibold text-ink-700">{Math.round(gap.student_score)}</span>
        {" · target "}
        <span className="font-semibold text-ink-700">{Math.round(gap.benchmark)}</span>
        {" · gap "}
        <span className="font-semibold text-danger-500">
          {Math.round(gap.gap_size)}
        </span>
        {gap.jd_frequency !== null
          ? ` · required in ${Math.round(gap.jd_frequency * 100)}% of JDs`
          : ""}
      </p>

      {gap.rationale ? (
        <div className="mt-3 rounded-lg border border-brand-100 bg-brand-50/50 p-3">
          <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden
            >
              <path d="M12 2 14 9l7 2-7 2-2 7-2-7-7-2 7-2z" />
            </svg>
            AI insight
          </p>
          <p className="mt-1 text-sm leading-relaxed text-ink-800">
            {gap.rationale}
          </p>
        </div>
      ) : (
        <Skeleton className="mt-3 h-4 w-full" label="Loading rationale" />
      )}

      {gap.signals.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-1.5 text-xs text-ink-500">
          {gap.signals.map((sig) => (
            <li
              key={sig}
              className="rounded-full border border-ink-200 bg-ink-50 px-2 py-0.5"
            >
              {sig}
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}
