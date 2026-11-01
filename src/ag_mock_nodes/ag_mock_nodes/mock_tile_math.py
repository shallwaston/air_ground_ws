"""Pure computation for mock 2.5D tiles, shared by tests and the ROS publisher."""

from __future__ import annotations

import math


def build_mock_tile_layers(width: int, height: int, phase: float) -> tuple[list[float], list[int]]:
    """Match the original mock tile values while evaluating trig terms once per row/column."""
    if width <= 0 or height <= 0:
        raise ValueError("tile dimensions must be positive")

    row_terms = [0.5 * math.sin(0.07 * row + phase) for row in range(height)]
    col_terms = [0.25 * math.cos(0.11 * col) for col in range(width)]
    elevation: list[float] = []
    traversability: list[int] = []
    for row_term in row_terms:
        for col_term in col_terms:
            height_value = float(row_term + col_term)
            elevation.append(height_value)
            traversability.append(255 if abs(height_value) < 0.45 else 64)
    return elevation, traversability
