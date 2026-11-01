"""Regression coverage for PR #2's real ROS endpoints, clocks, and TF input."""

import math
from pathlib import Path
import time

import pytest
import rclpy
from rclpy.qos import DurabilityPolicy, HistoryPolicy, ReliabilityPolicy
import yaml

from ag_interfaces.msg import Heartbeat
from ag_mock_nodes.ugv_map_tile_sub import UgvMapTileSub
from ag_monitor.delay_probe_sub import DelayProbeSub
import ag_monitor.system_monitor as monitor_module
from ag_monitor.system_monitor import SystemMonitor
from ag_network_tools import qos_profiles
from ag_network_tools.transforms import quaternion_from_euler
from ag_tf_tools.static_tf_loader import StaticTfLoader


@pytest.fixture
def ros_context():
    rclpy.init(args=[])
    yield
    rclpy.try_shutdown()


def test_monitor_expires_heartbeats_with_paused_sim_time(monkeypatch):
    now = [10_000_000_000]
    monkeypatch.setattr(monitor_module, 'monotonic_ns', lambda: now[0])
    rclpy.init(args=['--ros-args', '-p', 'use_sim_time:=true',
                     '-p', 'timeout_sec:=0.5', '-p', 'summary_period_sec:=0.5'])
    class ObservedMonitor(SystemMonitor):
        calls = 0

        def print_summary(self):
            self.calls += 1
            super().print_summary()

    node = ObservedMonitor()
    try:
        node.on_heartbeat(Heartbeat(node_name='expired', role='uav'))
        node.on_heartbeat(Heartbeat(node_name='live', role='ugv'))
        assert node.get_clock().now().nanoseconds == 0
        now[0] += 600_000_000
        node.on_heartbeat(Heartbeat(node_name='live', role='ugv'))
        deadline = time.monotonic() + 3
        while node.calls == 0 and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        assert node.calls > 0, 'summary timer stalled without /clock'
        assert set(node.heartbeats) == {'live'}
        assert set(node.heartbeat_last_seen_ns) == {'live'}
        assert node.get_clock().now().nanoseconds == 0
        assert node.last_seen_ns['/system/heartbeat'] == now[0]
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_report_endpoints_use_report_qos_and_partial_defaults(tmp_path, monkeypatch, ros_context):
    path = tmp_path / 'qos.yaml'
    path.write_text(yaml.safe_dump({'topics': {
        '/system/heartbeat': {'depth': 3},
        '/system/delay_report': {'depth': 7, 'reliability': 'best_effort'},
        '/tf_static': {'depth': 2},
    }}))
    monkeypatch.setenv('AG_QOS_CONFIG_PATH', str(path))
    nodes = [UgvMapTileSub(), DelayProbeSub(), SystemMonitor(), StaticTfLoader()]
    try:
        for node in nodes[:2]:
            assert node.report_pub.qos_profile.depth == 7
            assert node.report_pub.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
        report_sub = next(s for s in nodes[2].subscriptions if s.topic_name == '/system/delay_report')
        assert report_sub.qos_profile.depth == 7
        assert report_sub.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
        static_pub = next(p for p in nodes[3].publishers if p.topic_name == '/tf_static')
        assert static_pub.qos_profile.depth == 2
        assert static_pub.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
    finally:
        for node in nodes:
            node.destroy_node()


def test_qos_cache_is_private_and_reloads_edits(tmp_path, monkeypatch):
    path = tmp_path / 'qos.yaml'
    path.write_text('topics: {"/uav/map/tile": {depth: 17}}')
    calls = []
    original = yaml.safe_load
    def parse(stream):
        calls.append(1)
        return original(stream)
    monkeypatch.setattr(yaml, 'safe_load', parse)
    first = qos_profiles.load_qos_config(str(path))
    first['topics']['/uav/map/tile']['depth'] = 99
    profile = qos_profiles.get_qos_profile_for_topic('/uav/map/tile', str(path))
    assert profile.depth == 17
    assert profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
    assert len(calls) == 1
    path.write_text('topics: {"/uav/map/tile": {depth: 180}}')
    assert qos_profiles.get_qos_profile_for_topic('/uav/map/tile', str(path)).depth == 180
    assert len(calls) == 2


@pytest.mark.parametrize('data', [
    {'reliability': 'typo'}, {'durability': 'typo'}, {'history': 'typo'},
    {'depth': 0}, {'depth': -1}, {'depth': True}, {'depth': 1.5},
])
def test_invalid_qos_is_rejected(data):
    with pytest.raises(ValueError):
        qos_profiles.profile_from_dict(data)


def test_keep_all_zero_depth_and_missing_explicit_config(tmp_path):
    assert qos_profiles.profile_from_dict({'history': 'keep_all', 'depth': 0}).history == HistoryPolicy.KEEP_ALL
    with pytest.raises(FileNotFoundError):
        qos_profiles.load_qos_config(str(tmp_path / 'missing.yaml'))


@pytest.mark.parametrize('data', ['[]', 'topics: []', 'topics: {foo: []}'])
def test_malformed_qos_mapping(tmp_path, data):
    path = tmp_path / 'invalid.yaml'
    path.write_text(data)
    with pytest.raises(ValueError):
        qos_profiles.load_qos_config(str(path))


@pytest.mark.parametrize('transforms', [
    [{'parent': 'map', 'child': 'map'}],
    [{'parent': '', 'child': 'base'}],
    [{'parent': '/map', 'child': 'base'}],
    [{'parent': 'a', 'child': 'b'}, {'parent': 'b', 'child': 'a'}],
    [{'parent': 'a', 'child': 'b'}, {'parent': 'c', 'child': 'b'}],
    [{'parent': 'map', 'child': 'base', 'translation': {'x': float('nan')}}],
    [{'parent': 'map', 'child': 'base', 'rotation_rpy_rad': []}],
    [None],
])
def test_invalid_static_tf_rejected(tmp_path, transforms, ros_context):
    node = StaticTfLoader()
    try:
        path = tmp_path / 'tf.yaml'
        path.write_text(yaml.safe_dump({'transforms': transforms}))
        with pytest.raises(ValueError):
            node.load_transforms(str(path))
    finally:
        node.destroy_node()


@pytest.mark.parametrize('angles', [(0., 0., 0.), (.3, -.2, .7), (math.pi, 0., -math.pi)])
def test_shared_quaternion_is_normalized(angles):
    q = quaternion_from_euler(*angles)
    assert q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w == pytest.approx(1.)


def test_qos_yaml_copies_match_defaults():
    root = Path(__file__).resolve().parents[3]
    root_data = yaml.safe_load((root / 'config/qos/qos_profiles.yaml').read_text())
    installed_data = yaml.safe_load((root / 'src/ag_bringup/config/qos_profiles.yaml').read_text())
    assert root_data == installed_data == qos_profiles.DEFAULT_QOS_CONFIG
