import numpy as np
import pandas as pd
import pytest

from commercepulse.evidence import allocate, run, wape


def test_allocator_respects_constraints_and_objective():
    np.testing.assert_array_equal(allocate([4, 8, 9], [10, 20, -1], 10), [2, 8, 0])
    np.testing.assert_array_equal(allocate([4, 8], [10, 20], 100), [4, 8])
    with pytest.raises(ValueError):
        allocate([-1], [10], 2)


def test_wape_denominator_and_shape():
    assert wape([10, 20], [12, 19]) == 0.1
    for actual, predicted in [([0], [1]), ([1], [1, 2]), ([1], [np.nan])]:
        with pytest.raises(ValueError):
            wape(actual, predicted)


def test_chunk_independence_and_persisted_integrity(tmp_path):
    one = run(800, 60, tmp_path / "one", chunk_size=71, persist=True)
    two = run(800, 60, tmp_path / "two", chunk_size=127)
    assert one["event_key_sha256"] == two["event_key_sha256"]
    assert one["forecast"] == two["forecast"]
    assert one["scenarios"] == two["scenarios"]
    frame = pd.read_parquet(tmp_path / "one/events")
    journeys = pd.read_parquet(tmp_path / "one/journeys.parquet")
    assert len(frame) == 800 and frame.event_id.is_unique
    assert set(frame.journey_id) <= set(journeys.journey_id)
    assert frame.market.nunique() == 6
    assert frame.channel.nunique() == 3
    assert one["quality"]["failed_rows"] == 0
    with pytest.raises(FileExistsError):
        run(800, 60, tmp_path / "one", persist=True)


def test_invalid_scale(tmp_path):
    for events, journeys, chunk in [(5, 6, 1), (6, 5, 1), (10, 6, 0)]:
        with pytest.raises(ValueError):
            run(events, journeys, tmp_path, chunk_size=chunk)
