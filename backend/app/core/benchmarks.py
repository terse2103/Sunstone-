from app.models import TrackBenchmark

_REGISTRY: dict[str, TrackBenchmark] = {}


def register_tracks(tracks: dict[str, TrackBenchmark]) -> None:
    """Replace the in-memory track registry. Called by data/seed.load() at boot.

    Kept here (not in data/seed) so core/ stays import-independent of data/, per Rules §Code/1.
    """
    _REGISTRY.clear()
    _REGISTRY.update(tracks)


def get_track(name: str) -> TrackBenchmark:
    """Return the TrackBenchmark for `name`. Raises KeyError for unknown tracks (EdgeCases §1.3)."""
    if name not in _REGISTRY:
        raise KeyError(f"unknown_career_track: {name!r}")
    return _REGISTRY[name]


def all_track_names() -> list[str]:
    return sorted(_REGISTRY)
