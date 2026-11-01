"""Pure-Python regression tests; no running ROS graph is required."""

import math

import pytest

from ag_mock_nodes.mock_tile_math import build_mock_tile_layers
from ag_monitor.health_logic import age_seconds, expired_heartbeat_names


@pytest.mark.parametrize("width,height,phase", [
    (1, 1, 0.0), (3, 5, 1.0), (64, 64, 0.45),
    (256, 256, -3.2), (7, 2, 10000.15),
])
def test_mock_tile_layers_preserve_legacy_values(width, height, phase):
    elevation, traversability = build_mock_tile_layers(width, height, phase)
    assert len(elevation) == len(traversability) == width * height
    for index in range(width * height):
        row, col = divmod(index, width)
        expected = float(0.5 * math.sin(0.07 * row + phase) + 0.25 * math.cos(0.11 * col))
        assert elevation[index] == expected
        assert traversability[index] == (255 if abs(expected) < 0.45 else 64)


@pytest.mark.parametrize("width,height", [(0, 1), (1, 0), (-1, 5)])
def test_mock_tile_layers_reject_invalid_dimensions(width, height):
    with pytest.raises(ValueError):
        build_mock_tile_layers(width, height, 0.0)


def test_monotonic_liveness_age_and_stale_nodes():
    now_ns = 20_000_000_000
    heartbeat_ns = {"uav": 14_999_999_999, "ugv": 17_000_000_000}
    assert age_seconds(15_000_000_000, now_ns) == 5.0
    assert age_seconds(now_ns + 1, now_ns) == 0.0
    assert expired_heartbeat_names(heartbeat_ns, now_ns, 5.0) == ["uav"]
    assert expired_heartbeat_names({"uav": 15_000_000_000}, now_ns, 5.0) == []
