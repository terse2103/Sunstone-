import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { AtRiskAssessment, RiskLevel } from "../api/types";
import { DIMENSION_LABEL, formatSubskill } from "../lib/dimensions";

type SortKey = "name" | "readiness" | "risk" | "days";

interface Props {
  rows: AtRiskAssessment[];
  nameById: Record<string, string>;
  trackById: Record<string, string>;
}

const RISK_RANK: Record<RiskLevel, number> = {
  high: 0,
  medium: 1,
  low: 2,
  unknown: 3,
};

const RISK_STYLE: Record<RiskLevel, string> = {
  high: "bg-danger-500/10 text-danger-500 border-danger-500/40",
  medium: "bg-warning-500/10 text-warning-500 border-warning-500/40",
  low: "bg-success-500/10 text-success-500 border-success-500/40",
  unknown: "bg-ink-100 text-ink-600 border-ink-200",
};

export function AtRiskTable({ rows, nameById, trackById }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("readiness");
  const [asc, setAsc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = (nameById[a.student_id] ?? a.student_id).localeCompare(
            nameById[b.student_id] ?? b.student_id,
          );
          break;
        case "readiness":
          cmp = a.readiness - b.readiness;
          break;
        case "risk":
          cmp = RISK_RANK[a.risk_level] - RISK_RANK[b.risk_level];
          break;
        case "days":
          cmp = a.days_to_placement - b.days_to_placement;
          break;
      }
      if (cmp === 0) cmp = a.student_id.localeCompare(b.student_id);
      return asc ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, asc, nameById]);

  function toggleSort(next: SortKey) {
    if (next === sortKey) setAsc((v) => !v);
    else {
      setSortKey(next);
      setAsc(next !== "readiness" ? true : true);
    }
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-ink-200 bg-white shadow-sm">
      <table className="min-w-[640px] w-full text-left text-sm">
        <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
          <tr>
            <Th label="Student" active={sortKey === "name"} asc={asc} onClick={() => toggleSort("name")} />
            <th className="px-3 py-3 font-medium">Track</th>
            <Th label="Readiness" active={sortKey === "readiness"} asc={asc} onClick={() => toggleSort("readiness")} />
            <Th label="Risk" active={sortKey === "risk"} asc={asc} onClick={() => toggleSort("risk")} />
            <Th label="Days to placement" active={sortKey === "days"} asc={asc} onClick={() => toggleSort("days")} />
            <th className="px-3 py-3 font-medium">Primary gap</th>
            <th className="px-3 py-3" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((a) => {
            const name = nameById[a.student_id] ?? a.student_id;
            const track = trackById[a.student_id] ?? "—";
            return (
              <tr key={a.student_id} className="border-t border-ink-100 hover:bg-ink-50/60">
                <td className="px-3 py-3 max-w-[200px]">
                  <Link
                    to={`/counselor/student/${a.student_id}`}
                    className="block truncate font-medium text-ink-900 hover:text-brand-700"
                    title={name}
                  >
                    {name}
                  </Link>
                  <span className="text-xs text-ink-500">{a.student_id}</span>
                </td>
                <td className="px-3 py-3 text-ink-700">{track}</td>
                <td className="px-3 py-3 tabular-nums text-ink-900">
                  {Math.round(a.readiness)}
                </td>
                <td className="px-3 py-3">
                  <span
                    className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${RISK_STYLE[a.risk_level]}`}
                  >
                    {a.risk_level}
                  </span>
                </td>
                <td className="px-3 py-3 tabular-nums text-ink-700">{a.days_to_placement}</td>
                <td className="px-3 py-3 max-w-[220px] text-ink-700">
                  {a.primary_gap ? (
                    <span className="block truncate" title={formatSubskill(a.primary_gap.subskill)}>
                      {formatSubskill(a.primary_gap.subskill)}{" "}
                      <span className="text-xs text-ink-500">
                        ({DIMENSION_LABEL[a.primary_gap.dimension]})
                      </span>
                    </span>
                  ) : (
                    <span className="text-ink-400">—</span>
                  )}
                </td>
                <td className="px-3 py-3 text-right">
                  <Link
                    to={`/counselor/student/${a.student_id}`}
                    className="inline-flex items-center rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
                  >
                    Open brief
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({
  label,
  active,
  asc,
  onClick,
}: {
  label: string;
  active: boolean;
  asc: boolean;
  onClick: () => void;
}) {
  return (
    <th className="px-3 py-3 font-medium">
      <button
        type="button"
        onClick={onClick}
        className={
          "inline-flex items-center gap-1 transition-colors " +
          (active ? "text-ink-900" : "text-ink-500 hover:text-ink-800")
        }
        aria-sort={active ? (asc ? "ascending" : "descending") : "none"}
      >
        {label}
        <span aria-hidden className="text-[10px]">
          {active ? (asc ? "▲" : "▼") : "↕"}
        </span>
      </button>
    </th>
  );
}
