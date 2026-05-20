import { useState } from "react";
import type { EvalResult, EvalStatus, EvalsReport } from "../api/types";

const STATUS_STYLE: Record<EvalStatus, string> = {
  pass: "bg-success-500/10 text-success-500 border-success-500/40",
  fail: "bg-danger-500/10 text-danger-500 border-danger-500/40",
  not_run: "bg-ink-100 text-ink-600 border-ink-200",
};

const STATUS_LABEL: Record<EvalStatus, string> = {
  pass: "Pass",
  fail: "Fail",
  not_run: "Not run",
};

interface SuiteMeta {
  title: string;
  question: string;
  measures: string;
  passes: string;
}

// What each suite tests, in language a first-time viewer can follow.
// Keyed on the suite name emitted by evals/run.py.
const SUITE_META: Record<string, SuiteMeta> = {
  score_calibration: {
    title: "Score Calibration",
    question:
      "Does the readiness score correctly separate placed from not-placed students?",
    measures:
      "10 golden profiles, each labelled placed (overall score > 70), not_placed (< 50), or borderline (50–70). Plus a sensitivity pair — the same student with +15 added to every cycle of one sub-skill, where the overall score is expected to move meaningfully.",
    passes:
      "Directional accuracy ≥ 0.9 (≥ 9 of 10 profiles land in the correct bucket) AND the sensitivity pair shows an overall-score delta of ≥ 1.0 point.",
  },
  gap_relevance: {
    title: "Gap Relevance",
    question: "Are the top-3 priority gaps the right ones?",
    measures:
      "5 hand-labelled profiles. For each, the engine must return the same three sub-skill gaps a human expert would pick, with the #1 priority correct on every profile. Tied-priority cases are present too, to exercise the stable alphabetical tiebreak.",
    passes:
      "Top-3 set matches expected on ≥ 4 of 5 profiles AND the #1 gap matches on all 5.",
  },
  early_warning: {
    title: "Early Warning",
    question: "Are we catching at-risk students without raising false alarms?",
    measures:
      "8 trajectories — 4 truly at-risk (declining scores, flat or negative trajectory, ≥ 60 days to placement) and 4 negatives that each test a different exemption (improving slope, above-threshold readiness, strong overall, closed placement window). For each, the engine must agree with the human label.",
    passes:
      "Recall = 1.0 (every truly at-risk student is flagged) AND no more than 1 false positive across the 4 negatives.",
  },
};

const METRIC_LABEL: Record<string, string> = {
  directional_accuracy: "Directional accuracy",
  correct: "Cases correct",
  total: "Cases total",
  min_accuracy: "Required accuracy",
  sensitivity_delta: "Sensitivity Δ overall",
  sensitivity_min_delta: "Required sensitivity Δ",
  profiles_full_match: "Profiles fully matched",
  profiles_first_correct: "Profiles with #1 correct",
  profiles_total: "Profiles total",
  full_match_required: "Full matches required",
  first_correct_required: "#1 matches required",
  recall: "Recall",
  true_positives: "True positives",
  false_negatives: "False negatives",
  false_positives: "False positives",
  false_positive_rate: "False-positive rate",
  min_recall: "Required recall",
  max_false_positives: "Max false positives allowed",
};

interface Props {
  report: EvalsReport;
}

export function EvalsResultsViewer({ report }: Props) {
  if (report.status === "not_run" || report.suites.length === 0) {
    return (
      <div className="rounded-2xl border border-ink-200 bg-white p-6 text-center md:p-10">
        <p className="text-base font-medium text-ink-700">Evals not run yet.</p>
        <p className="mt-1 text-sm text-ink-500">
          Run <code className="rounded bg-ink-100 px-1.5 py-0.5 text-xs">python evals/run.py</code>{" "}
          and commit <code className="rounded bg-ink-100 px-1.5 py-0.5 text-xs">evals/results/report.json</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <span className="flex items-center gap-2">
          <span
            className={`rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${STATUS_STYLE[report.status]}`}
          >
            {STATUS_LABEL[report.status]}
          </span>
          <span className="text-ink-700">
            {report.suites.length} suite{report.suites.length === 1 ? "" : "s"}
          </span>
        </span>
        {report.ran_at ? (
          <span className="text-ink-500">Ran at {report.ran_at}</span>
        ) : null}
      </div>

      <ul className="space-y-3">
        {report.suites.map((suite) => (
          <SuiteRow key={suite.name} suite={suite} />
        ))}
      </ul>
    </div>
  );
}

function SuiteRow({ suite }: { suite: EvalResult }) {
  const [open, setOpen] = useState(suite.status === "fail");
  const meta = SUITE_META[suite.name];
  const metricEntries = Object.entries(suite.metrics);
  const displayTitle = meta?.title ?? humanize(suite.name);

  return (
    <li className="overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-ink-50 md:px-5"
        aria-expanded={open}
      >
        <span className="flex flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${STATUS_STYLE[suite.status]}`}
            >
              {STATUS_LABEL[suite.status]}
            </span>
            <span className="font-medium text-ink-900">{displayTitle}</span>
            <span className="text-xs text-ink-500">
              {suite.cases.length} case{suite.cases.length === 1 ? "" : "s"}
            </span>
          </span>
          {meta ? (
            <span className="text-xs text-ink-600 md:text-sm">
              {meta.question}
            </span>
          ) : null}
        </span>
        <span aria-hidden className="pt-0.5 text-ink-400">
          {open ? "▾" : "▸"}
        </span>
      </button>

      {open ? (
        <div className="border-t border-ink-100 bg-ink-50/40 px-4 py-3 md:px-5">
          {meta ? (
            <div className="mb-3 grid gap-3 sm:grid-cols-2">
              <ExplainerBlock label="What this measures" body={meta.measures} />
              <ExplainerBlock label="Pass criteria" body={meta.passes} />
            </div>
          ) : null}

          {metricEntries.length > 0 ? (
            <dl className="mb-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
              {metricEntries.map(([k, v]) => (
                <div key={k} className="rounded-md bg-white p-2 ring-1 ring-ink-200">
                  <dt className="text-ink-500">{METRIC_LABEL[k] ?? humanize(k)}</dt>
                  <dd className="font-semibold tabular-nums text-ink-900">
                    {formatMetric(v)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}

          {suite.cases.length === 0 ? (
            <p className="text-xs text-ink-500">No per-case detail emitted.</p>
          ) : (
            <ul className="space-y-2 text-xs">
              {suite.cases.map((c, i) => (
                <li
                  key={`${c.name}-${i}`}
                  className="rounded-md border border-ink-200 bg-white p-3"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-medium text-ink-900 break-words">
                      {c.name}
                    </span>
                    <span
                      className={
                        "rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase " +
                        (c.passed
                          ? STATUS_STYLE.pass
                          : STATUS_STYLE.fail)
                      }
                    >
                      {c.passed ? "Pass" : "Fail"}
                    </span>
                  </div>
                  {c.note ? (
                    <p className="mt-1 text-ink-700">{c.note}</p>
                  ) : null}
                  {c.expected !== undefined || c.actual !== undefined ? (
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <CodeBlock label="Expected" value={c.expected} />
                      <CodeBlock label="Actual" value={c.actual} />
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </li>
  );
}

function ExplainerBlock({ label, body }: { label: string; body: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
        {label}
      </p>
      <p className="mt-1 text-sm text-ink-700">{body}</p>
    </div>
  );
}

function CodeBlock({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null) return null;
  const rendered =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-ink-500">{label}</p>
      <pre className="mt-1 max-h-40 overflow-auto rounded bg-ink-900/95 p-2 text-[11px] leading-snug text-ink-100">
        {rendered}
      </pre>
    </div>
  );
}

function formatMetric(v: number): string {
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(2);
}

function humanize(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/^\w/, (c) => c.toUpperCase());
}
