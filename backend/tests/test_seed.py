from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data import seed


def _good_benchmarks() -> dict:
    return {
        "BFSI": {
            "weights": {"E": 0.2, "L": 0.2, "Q": 0.3, "D": 0.3},
            "subskills": {
                "business_communication": {"dimension": "E", "benchmark": 70},
                "logical_reasoning": {"dimension": "L", "benchmark": 75},
                "quant_aptitude": {"dimension": "Q", "benchmark": 80},
                "banking_fundamentals": {"dimension": "D", "benchmark": 75},
            },
            "jd_frequency": {"banking_fundamentals": 0.78},
        }
    }


def _good_students() -> dict:
    return {
        "students": [
            {
                "id": "STU_X",
                "name": "Test Student",
                "program": "MBA",
                "campus": "Pune",
                "career_track": "BFSI",
                "days_to_placement": 120,
                "assessments": [
                    {"subskill": "business_communication", "score": 70, "cycle": 1},
                    {"subskill": "business_communication", "score": 72, "cycle": 2},
                ],
                "attendance_pct": {"E": 85, "L": 90, "Q": 90, "D": 88},
                "time_on_task_hrs": {"E": 18, "L": 22, "Q": 25, "D": 24},
                "recent_signals": [],
            }
        ]
    }


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_load_real_seed_succeeds() -> None:
    """The committed seed files must load without error — boot smoke test."""
    seed.load()
    assert set(seed.BENCHMARKS) == {"BFSI", "Analytics", "Digital Marketing"}
    assert len(seed.STUDENTS) == 12
    for student in seed.STUDENTS.values():
        assert student.career_track in seed.BENCHMARKS


def test_load_with_overrides(tmp_path: Path) -> None:
    bm = _write(tmp_path, "bm.json", _good_benchmarks())
    st = _write(tmp_path, "st.json", _good_students())
    seed.load(benchmarks_path=bm, students_path=st)
    assert "BFSI" in seed.BENCHMARKS
    assert "STU_X" in seed.STUDENTS


def test_weights_must_sum_to_one(tmp_path: Path) -> None:
    """EdgeCases §2.2 — boot fails with invalid_weights including the offending track."""
    bad = _good_benchmarks()
    bad["BFSI"]["weights"]["E"] = 0.5  # now sums to 1.3
    bm = _write(tmp_path, "bm.json", bad)
    st = _write(tmp_path, "st.json", _good_students())

    with pytest.raises(seed.SeedError, match=r"invalid_weights.*BFSI"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_unknown_career_track_fails_boot(tmp_path: Path) -> None:
    """EdgeCases §1.3 — student references a track that doesn't exist."""
    bad_students = _good_students()
    bad_students["students"][0]["career_track"] = "Pottery"
    bm = _write(tmp_path, "bm.json", _good_benchmarks())
    st = _write(tmp_path, "st.json", bad_students)

    with pytest.raises(seed.SeedError, match=r"unknown career_track.*Pottery"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_duplicate_assessment_cycle_fails_boot(tmp_path: Path) -> None:
    """EdgeCases §1.5 — duplicate (subskill, cycle) tuple is rejected, never silently overwritten."""
    bad_students = _good_students()
    bad_students["students"][0]["assessments"].append(
        {"subskill": "business_communication", "score": 90, "cycle": 1}
    )
    bm = _write(tmp_path, "bm.json", _good_benchmarks())
    st = _write(tmp_path, "st.json", bad_students)

    with pytest.raises(seed.SeedError, match=r"duplicate assessment.*business_communication.*cycle=1"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_duplicate_student_id_fails_boot(tmp_path: Path) -> None:
    bad_students = _good_students()
    bad_students["students"].append(dict(bad_students["students"][0]))
    bm = _write(tmp_path, "bm.json", _good_benchmarks())
    st = _write(tmp_path, "st.json", bad_students)

    with pytest.raises(seed.SeedError, match=r"duplicate student id.*STU_X"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_malformed_benchmarks_schema_fails_boot(tmp_path: Path) -> None:
    bad = _good_benchmarks()
    bad["BFSI"]["weights"] = "not-a-dict"
    bm = _write(tmp_path, "bm.json", bad)
    st = _write(tmp_path, "st.json", _good_students())

    with pytest.raises(seed.SeedError, match=r"BFSI.*failed schema"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_missing_seed_file_fails_clean(tmp_path: Path) -> None:
    bm = tmp_path / "does_not_exist.json"
    st = _write(tmp_path, "st.json", _good_students())

    with pytest.raises(seed.SeedError, match=r"seed file not found"):
        seed.load(benchmarks_path=bm, students_path=st)


def test_invalid_json_fails_clean(tmp_path: Path) -> None:
    bm = tmp_path / "bm.json"
    bm.write_text("{ not valid json", encoding="utf-8")
    st = _write(tmp_path, "st.json", _good_students())

    with pytest.raises(seed.SeedError, match=r"invalid JSON"):
        seed.load(benchmarks_path=bm, students_path=st)
