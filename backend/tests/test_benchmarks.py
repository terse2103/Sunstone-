import pytest

from app.core import benchmarks as benchmarks_module
from app.data import seed


def test_get_track_returns_expected_shape() -> None:
    seed.load()
    track = benchmarks_module.get_track("BFSI")
    assert track.name == "BFSI"
    assert abs(sum(track.weights.values()) - 1.0) < 1e-9
    assert "banking_fundamentals" in track.subskills
    assert track.subskills["banking_fundamentals"].dimension == "D"
    assert track.subskills["banking_fundamentals"].benchmark == 75
    assert track.jd_frequency["banking_fundamentals"] == pytest.approx(0.78)


def test_get_track_unknown_raises() -> None:
    seed.load()
    with pytest.raises(KeyError, match="unknown_career_track"):
        benchmarks_module.get_track("Pottery")


def test_all_track_names_after_load() -> None:
    seed.load()
    assert benchmarks_module.all_track_names() == ["Analytics", "BFSI", "Digital Marketing"]


def test_register_tracks_replaces_registry() -> None:
    seed.load()
    benchmarks_module.register_tracks({})
    assert benchmarks_module.all_track_names() == []
    with pytest.raises(KeyError):
        benchmarks_module.get_track("BFSI")
    seed.load()  # restore for subsequent tests in this process
