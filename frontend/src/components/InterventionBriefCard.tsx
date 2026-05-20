import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import type {
  AtRiskAssessment,
  InterventionBrief,
  PrimaryLever,
  RiskLevel,
} from "../api/types";
import { DIMENSION_LABEL, formatSubskill } from "../lib/dimensions";

const RISK_STYLE: Record<RiskLevel, string> = {
  high: "bg-danger-500/10 text-danger-500 border-danger-500/40",
  medium: "bg-warning-500/10 text-warning-500 border-warning-500/40",
  low: "bg-success-500/10 text-success-500 border-success-500/40",
  unknown: "bg-ink-100 text-ink-600 border-ink-200",
};

const LEVER_LABEL: Record<PrimaryLever, string> = {
  assessment_scores: "Raising assessment scores",
  attendance: "Improving attendance",
  time_on_task: "Increasing time on task",
};

const LEVER_HINT: Record<PrimaryLever, string> = {
  assessment_scores:
    "The deepest weighted gap is in academic performance — focused practice on the sub-skill below is the highest-impact move.",
  attendance:
    "Scores are close to benchmark, but missed sessions are the biggest drag on this dimension's score.",
  time_on_task:
    "Scores and attendance are close to benchmark; engagement / study hours are the biggest drag.",
};

interface Props {
  studentId: string;
  brief: InterventionBrief;
  assessment: AtRiskAssessment | null;
}

export function InterventionBriefCard({ studentId, brief, assessment }: Props) {
  const action = useMutation({
    mutationFn: () => api.markAction(studentId),
  });

  return (
    <article className="rounded-2xl border border-ink-200 bg-white p-5 shadow-sm md:p-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-ink-500">
            Intervention brief
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-semibold normal-case tracking-normal text-white">
              <svg
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden
              >
                <path d="M12 2 14 9l7 2-7 2-2 7-2-7-7-2 7-2z" />
              </svg>
              AI
            </span>
          </h2>
          {assessment ? (
            <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${RISK_STYLE[assessment.risk_level]}`}
              >
                {assessment.risk_level} risk
              </span>
              <span className="text-ink-700">
                Readiness <span className="font-semibold">{Math.round(assessment.readiness)}</span>
              </span>
              <span className="text-ink-500">
                · {assessment.days_to_placement}d to placement
              </span>
            </p>
          ) : null}
        </div>
      </header>

      <ol className="mt-4 space-y-2">
        {brief.lines.map((line, i) => (
          <li
            key={i}
            className="flex gap-2 text-sm leading-relaxed text-ink-800"
          >
            <span className="inline-flex h-5 min-w-5 flex-none items-center justify-center rounded-full bg-brand-100 text-[10px] font-semibold text-brand-700">
              {i + 1}
            </span>
            <span className="break-words">{line}</span>
          </li>
        ))}
      </ol>

      {assessment?.primary_gap ? (
        <div className="mt-5 rounded-lg border border-ink-200 bg-ink-50 p-3 text-sm md:p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Primary gap · start with
          </p>
          {assessment.primary_lever ? (
            <p className="mt-1 text-base font-semibold text-ink-900">
              {LEVER_LABEL[assessment.primary_lever]}
            </p>
          ) : null}
          <p className="mt-1 text-sm text-ink-800">
            in {formatSubskill(assessment.primary_gap.subskill)}{" "}
            <span className="text-ink-500">
              ({DIMENSION_LABEL[assessment.primary_gap.dimension]})
            </span>
          </p>
          {assessment.primary_lever ? (
            <p className="mt-2 text-xs text-ink-600">
              {LEVER_HINT[assessment.primary_lever]}
            </p>
          ) : null}
          <p className="mt-2 text-xs tabular-nums text-ink-500">
            Current score{" "}
            <span className="font-semibold text-ink-700">
              {Math.round(assessment.primary_gap.student_score)}
            </span>{" "}
            · Benchmark{" "}
            <span className="font-semibold text-ink-700">
              {Math.round(assessment.primary_gap.benchmark)}
            </span>
          </p>
        </div>
      ) : null}

      {brief.contributing_signals.length > 0 ? (
        <section className="mt-5">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-500">
            Contributing signals
          </p>
          <ul className="mt-2 flex flex-wrap gap-1.5 text-xs">
            {brief.contributing_signals.map((sig) => (
              <li
                key={sig}
                className="rounded-full border border-ink-200 bg-white px-2 py-0.5 text-ink-700"
                title={sig}
              >
                {sig}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => action.mutate()}
          disabled={action.isPending || action.isSuccess}
          className="inline-flex min-h-[44px] items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-ink-300"
        >
          {action.isSuccess
            ? "Action recorded"
            : action.isPending
              ? "Saving…"
              : "Mark action taken"}
        </button>
        {action.isError ? (
          <p role="alert" className="text-sm text-danger-500">
            {action.error instanceof ApiError
              ? action.error.message
              : "Couldn’t save. Try again."}
          </p>
        ) : null}
        {action.isSuccess ? (
          <p className="text-xs text-ink-500">
            Stored in memory — counselor actions reset on backend restart.
          </p>
        ) : null}
      </footer>
    </article>
  );
}
