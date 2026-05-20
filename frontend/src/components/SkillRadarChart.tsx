import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { ReadinessResult } from "../api/types";
import { DIMENSION_LABEL, DIMENSION_ORDER } from "../lib/dimensions";

interface Props {
  readiness: ReadinessResult;
}

export function SkillRadarChart({ readiness }: Props) {
  const byDim = new Map(readiness.dimensions.map((d) => [d.dimension, d]));
  const data = DIMENSION_ORDER.map((dim) => {
    const ds = byDim.get(dim);
    return {
      dimension: DIMENSION_LABEL[dim],
      student: Math.round(ds?.score ?? 0),
      benchmark: Math.round(ds?.benchmark ?? 0),
    };
  });

  const allZero = data.every((d) => d.student === 0);

  return (
    <article className="rounded-2xl border border-ink-200 bg-white p-5 shadow-sm md:p-6">
      <header>
        <h2 className="text-sm font-medium uppercase tracking-wide text-ink-500">
          ELQD Skill Map
        </h2>
        <p className="text-xs text-ink-500">Student vs. {readiness.track} target</p>
      </header>

      <div className="mx-auto mt-3 aspect-square w-full max-w-md">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="var(--color-ink-200)" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fontSize: 12, fill: "var(--color-ink-600)" }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: "var(--color-ink-400)" }}
            />
            <Radar
              name="Benchmark"
              dataKey="benchmark"
              stroke="var(--color-ink-500)"
              fill="var(--color-ink-400)"
              fillOpacity={0.15}
            />
            <Radar
              name="Student"
              dataKey="student"
              stroke="var(--color-brand-600)"
              fill="var(--color-brand-500)"
              fillOpacity={0.35}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--color-ink-200)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {allZero ? (
        <p className="mt-2 text-center text-xs text-ink-500">
          No assessment data yet.
        </p>
      ) : null}
    </article>
  );
}
