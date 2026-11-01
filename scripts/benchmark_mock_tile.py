#!/usr/bin/env python3
"""Compare legacy and current map generation under the same ROS runtime.

Source the built workspace first. This reports local callback cost, including
message construction and ROS publication without subscribers, not network QoS
or delivered throughput. It does not change branches or tracked files.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import timeit

import rclpy

from ag_mock_nodes.mock_tile_math import build_mock_tile_layers
from ag_mock_nodes.uav_mock_map_tile_pub import UavMockMapTilePub


def legacy_layers(width, height, phase):
    elevation, traversability = [], []
    for index in range(width * height):
        row = index // width
        col = index % width
        value = 0.5 * math.sin(0.07 * row + phase) + 0.25 * math.cos(0.11 * col)
        elevation.append(float(value))
        traversability.append(255 if abs(value) < 0.45 else 64)
    return elevation, traversability


def median_ms(function, count, repeats):
    return statistics.median(timeit.repeat(function, number=count, repeat=repeats)) / count * 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-ref', default='e129564eb5de9125209600f63e4112a85338c02f')
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(
        ['git', 'show', f'{options.baseline_ref}:src/ag_mock_nodes/ag_mock_nodes/uav_mock_map_tile_pub.py'],
        cwd=root, text=True)
    with tempfile.TemporaryDirectory(prefix='ag-map-benchmark-') as directory:
        baseline_path = Path(directory) / 'baseline_map.py'
        baseline_path.write_text(source)
        spec = importlib.util.spec_from_file_location('baseline_map', baseline_path)
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)
        results = []
        for size, count in [(64, 100), (256, 10)]:
            assert legacy_layers(size, size, .45) == build_mock_tile_layers(size, size, .45)
            sample = {'size': size, 'repeats': 7, 'calls_per_repeat': count}
            for name, function in [('legacy', legacy_layers), ('optimized', build_mock_tile_layers)]:
                sample[name + '_layers_ms'] = median_ms(lambda: function(size, size, .45), count, 7)
            rclpy.init(args=['--ros-args', '-p', f'tile_width:={size}', '-p', f'tile_height:={size}'])
            try:
                for name, cls in [('legacy', baseline.UavMockMapTilePub), ('optimized', UavMockMapTilePub)]:
                    node = cls()
                    try:
                        node.timer.cancel()
                        sample[name + '_callback_ms'] = median_ms(node.on_timer, count, 7)
                    finally:
                        node.destroy_node()
            finally:
                rclpy.try_shutdown()
            results.append(sample)
        print(json.dumps({'baseline': options.baseline_ref, 'python': sys.version.split()[0],
                          'subscribers': 0, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
