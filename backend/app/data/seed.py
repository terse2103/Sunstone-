from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.core import benchmarks as benchmarks_registry
from app.models import Student, TrackBenchmark

DATA_DIR = Path(__file__).parent
WEIGHT_TOLERANCE = 1e-6

BENCHMARKS: dict[str, TrackBenchmark] = {}
STUDENTS: dict[str, Student] = {}


class SeedError(ValueError):
    """Raised when seed data is malformed. Surfaced at boot to fail fast."""


def load(
    *,
    benchmarks_path: Path | None = None,
    students_path: Path | None = None,
) -> None:
    """Load and validate JSON seed into module-level dicts.

    Fails fast on:
    - schema violations (Pydantic)
    - track weights not summing to 1.0 (EdgeCases §2.2)
    - unknown student career_track (EdgeCases §1.3)
    - duplicate (subskill, cycle) per student (EdgeCases §1.5)
    """
    BENCHMARKS.clear()
    STUDENTS.clear()

    bm_path = benchmarks_path or (DATA_DIR / "benchmarks.json")
    st_path = students_path or (DATA_DIR / "students.json")

    BENCHMARKS.update(_load_benchmarks(bm_path))
    STUDENTS.update(_load_students(st_path, known_tracks=set(BENCHMARKS)))
    benchmarks_registry.register_tracks(BENCHMARKS)


def _load_benchmarks(path: Path) -> dict[str, TrackBenchmark]:
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise SeedError(f"{path}: benchmarks file must be a JSON object at top level")

    out: dict[str, TrackBenchmark] = {}
    for track_name, payload in raw.items():
        if not isinstance(payload, dict):
            raise SeedError(f"{path}: track {track_name!r} body must be an object")
        try:
            track = TrackBenchmark(name=track_name, **payload)
        except ValidationError as exc:
            raise SeedError(f"track {track_name!r} failed schema: {exc}") from exc

        _validate_weights(track)
        out[track_name] = track
    return out


def _validate_weights(track: TrackBenchmark) -> None:
    total = sum(track.weights.values())
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise SeedError(
            f"invalid_weights: track {track.name!r} weights sum to {total}, expected 1.0"
        )


def _load_students(path: Path, *, known_tracks: set[str]) -> dict[str, Student]:
    raw = _read_json(path)
    if not isinstance(raw, dict) or "students" not in raw:
        raise SeedError(f"{path}: students file must have a top-level 'students' array")
    if not isinstance(raw["students"], list):
        raise SeedError(f"{path}: 'students' must be an array")

    out: dict[str, Student] = {}
    for entry in raw["students"]:
        if not isinstance(entry, dict):
            raise SeedError(f"{path}: each student entry must be an object")
        try:
            student = Student(**entry)
        except ValidationError as exc:
            sid = entry.get("id", "<missing id>")
            raise SeedError(f"student {sid!r} failed schema: {exc}") from exc

        if student.career_track not in known_tracks:
            raise SeedError(
                f"student {student.id!r} has unknown career_track "
                f"{student.career_track!r}; known tracks: {sorted(known_tracks)}"
            )

        seen: set[tuple[str, int]] = set()
        for a in student.assessments:
            key = (a.subskill, a.cycle)
            if key in seen:
                raise SeedError(
                    f"student {student.id!r}: duplicate assessment "
                    f"subskill={a.subskill!r} cycle={a.cycle}"
                )
            seen.add(key)

        if student.id in out:
            raise SeedError(f"duplicate student id {student.id!r}")
        out[student.id] = student
    return out


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SeedError(f"seed file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SeedError(f"{path}: invalid JSON — {exc}") from exc
