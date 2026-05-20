import type { ReadinessResult } from "../api/types";
import {
  DIMENSION_LABEL,
  DIMENSION_ORDER,
  RISK_BAND_LABEL,
  RISK_BAND_STYLE,
  riskBand,
} from "../lib/dimensions";

interface Props {
  readiness: ReadinessResult;
}

export function ReadinessScoreCard({ readiness }: Props) {
  const band = riskBand(readiness.overall);
  const dimByKey = new Map(readiness.dimensions.map((d) => [d.dimension, d]));

  return (
    <article className="rounded-2xl border border-ink-200 bg-white p-5 shadow-sm md:p-6">
      <header className="flex items-baseline justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium uppercase tracking-wide text-ink-500">
            Readiness
          </h2>
          <p className="text-xs text-ink-500">Track: {readiness.track}</p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${RISK_BAND_STYLE[band]}`}
        >
          {RISK_BAND_LABEL[band]}
        </span>
      </header>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-5xl font-semibold text-ink-900 md:text-6xl">
          {Math.round(readiness.overall)}
        </span>
        <span className="text-base text-ink-500">/ 100</span>
      </div>

      <ul className="mt-5 space-y-3">
        {DIMENSION_ORDER.map((dim) => {
          const ds = dimByKey.get(dim);
          if (!ds) return null;
          const score = Math.round(ds.score);
          const benchmark = Math.round(ds.benchmark);
          return (
            <li key={dim} aria-label={`${DIMENSION_LABEL[dim]} score`}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="font-medium text-ink-700">
                  {DIMENSION_LABEL[dim]}
                </span>
                <span className="tabular-nums text-ink-700">
                  <span className="font-semibold text-ink-900">{score}</span>
                  <span className="text-ink-400"> / target {benchmark}</span>
                </span>
              </div>
              <div className="relative mt-1 h-2 w-full overflow-hidden rounded-full bg-ink-100">
                <div
                  className="h-full rounded-full bg-brand-500"
                  style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                />
                {benchmark > 0 ? (
                  <div
                    aria-hidden
                    className="absolute top-0 h-full w-0.5 bg-ink-700"
                    style={{ left: `${Math.min(100, Math.max(0, benchmark))}%` }}
                    title={`Target ${benchmark}`}
                  />
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
