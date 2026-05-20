"""Sub-skill gap ranking against track benchmarks.

For each sub-skill the track declares, compute ``gap_size = benchmark - student_score``
(student_score = mean across the student's cycles for that sub-skill, or 0 if
absent — EdgeCases §1.4). Positive gaps are ranked by
``priority_score = gap_size * dimension_weight``, with sub-skill name as the
stable tiebreaker (EdgeCases §3.3).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models import Assessment, Gap, Student, TrackBenchmark


def compute_gaps(student: Student, track: TrackBenchmark) -> list[Gap]:
    """Return all positive gaps for the student, ranked by priority.

    Gaps with ``gap_size <= 0`` are filtered (EdgeCases §3.4). Sub-skills the
    student has no data for are treated as score = 0 and flagged in the gap's
    ``signals`` list (EdgeCases §1.4). Sorting is deterministic: priority desc,
    then sub-skill name asc (EdgeCases §3.3).
    """
    by_subskill = _avg_scores_by_subskill(student.assessments)

    raw: list[dict] = []
    for subskill, bench in track.subskills.items():
        scores = by_subskill.get(subskill)
        signals: list[str] = []
        if scores is None:
            student_score = 0.0
            signals.append(f"no_data:{subskill}")
        else:
            student_score = scores

        gap_size = bench.benchmark - student_score
        if gap_size <= 0:
            continue

        dim_weight = track.weights.get(bench.dimension, 0.0)
        priority = gap_size * dim_weight

        raw.append(
            {
                "subskill": subskill,
                "dimension": bench.dimension,
                "student_score": student_score,
                "benchmark": bench.benchmark,
                "gap_size": gap_size,
                "priority_score": priority,
                "jd_frequency": track.jd_frequency.get(subskill),
                "signals": signals,
            }
        )

    raw.sort(key=lambda g: (-g["priority_score"], g["subskill"]))
    return [Gap(rank=i + 1, **g) for i, g in enumerate(raw)]


def top_n_gaps(student: Student, track: TrackBenchmark, n: int = 3) -> list[Gap]:
    """Top-N gaps by priority. Returns fewer than ``n`` when not enough qualify
    (EdgeCases §3.2). Returns an empty list for students who exceed every
    benchmark (EdgeCases §3.1). Never pads with synthetic gaps.
    """
    if n <= 0:
        return []
    return compute_gaps(student, track)[:n]


def _avg_scores_by_subskill(assessments: Iterable[Assessment]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for a in assessments:
        buckets[a.subskill].append(a.score)
    return {k: sum(v) / len(v) for k, v in buckets.items()}
