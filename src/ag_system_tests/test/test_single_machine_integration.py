"""Launch the real graph and require live DDS data, TF, QoS, and clean exit."""

import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import ReliabilityPolicy
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener
import yaml

from ag_interfaces.msg import DelayProbe, Heartbeat, MapTile, TargetInfo
from ag_network_tools.qos_profiles import get_qos_profile_for_topic


def test_single_machine_messages_tf_custom_qos_and_shutdown(tmp_path):
    qos_path = tmp_path / 'qos.yaml'
    qos_path.write_text(yaml.safe_dump({'topics': {
        '/uav/map/tile': {'depth': 2, 'reliability': 'best_effort'}}}))
    rclpy.init(args=[])
    probe = Node('integration_probe')
    counts, latest = {}, {}
    subscriptions = []
    def receive(topic, msg):
        counts[topic] = counts.get(topic, 0) + 1
        latest[topic] = msg
    topics = {'/uav/odom': Odometry, '/uav/map/tile': MapTile,
              '/uav/targets/current': TargetInfo, '/system/heartbeat': Heartbeat,
              '/system/delay_probe': DelayProbe, '/system/delay_report': String}
    for topic, message_type in topics.items():
        subscriptions.append(probe.create_subscription(
            message_type, topic, lambda msg, t=topic: receive(t, msg),
            get_qos_profile_for_topic(topic, str(qos_path))))
    buffer = Buffer()
    listener = TransformListener(buffer, probe,
        qos=get_qos_profile_for_topic('/tf'),
        static_qos=get_qos_profile_for_topic('/tf_static'))
    pairs = [('map', 'uav/base_link'), ('map', 'ugv/odom'), ('ugv/odom', 'ugv/base_link')]
    log_path = tmp_path / 'single-machine.log'
    with log_path.open('w+') as log:
        process = subprocess.Popen(
            ['ros2', 'launch', 'ag_bringup', 'single_machine_mock.launch.py',
             f'qos_config:={qos_path}'],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                assert process.poll() is None, f'launch exited early; see {log_path}'
                rclpy.spin_once(probe, timeout_sec=0.1)
                tf_ready = all(buffer.can_transform(target, source, Time()) for target, source in pairs)
                if all(counts.get(topic, 0) >= 2 for topic in topics) and tf_ready:
                    break
            assert all(counts.get(topic, 0) >= 2 for topic in topics), counts
            for target, source in pairs:
                buffer.lookup_transform(target, source, Time())
            tile = latest['/uav/map/tile']
            assert tile.width == tile.height == 64
            assert len(tile.elevation) == len(tile.traversability) == 4096
            assert latest['/uav/odom'].header.frame_id == 'map'
            assert latest['/uav/odom'].child_frame_id == 'uav/base_link'
            endpoints = probe.get_publishers_info_by_topic('/uav/map/tile')
            # DDS discovery does not expose KEEP_LAST depth on every RMW.
            assert endpoints and all(
                e.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT for e in endpoints)
            process.send_signal(signal.SIGINT)
            process.wait(timeout=15)
            log.seek(0)
            output = log.read()
            assert process.returncode == 0, output
            assert 'Traceback' not in output, output
            assert 'process has died' not in output, output
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    import os
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            probe.destroy_node()
            rclpy.try_shutdown()


def test_transient_local_map_delivered_to_late_subscriber():
    rclpy.init(args=[])
    node = Node('late_joiner_probe')
    try:
        qos = get_qos_profile_for_topic('/uav/map/tile')
        publisher = node.create_publisher(MapTile, '/uav/map/tile', qos)
        publisher.publish(MapTile(seq=123, width=1, height=1, elevation=[0.], traversability=[255]))
        received = []
        subscription = node.create_subscription(MapTile, '/uav/map/tile', received.append, qos)
        deadline = time.monotonic() + 5
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        assert received and received[0].seq == 123
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
