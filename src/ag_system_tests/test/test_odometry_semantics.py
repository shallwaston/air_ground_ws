"""Verify the synthetic Odometry and TF agree with ROS frame conventions."""

import math
from types import SimpleNamespace

import pytest
import rclpy
from rclpy.time import Time

from ag_mock_nodes.uav_mock_odom_tf_pub import UavMockOdomTfPub


@pytest.mark.parametrize('seconds', [0., 4., 10.])
def test_odometry_twist_matches_pose_derivative_in_child_frame(seconds, monkeypatch):
    rclpy.init(args=[])
    node = UavMockOdomTfPub()
    try:
        odometry, transforms = [], []
        node.start_time_sec = 0.
        monkeypatch.setattr(node, 'get_clock', lambda: SimpleNamespace(now=lambda: Time(seconds=seconds)))
        node.odom_pub = SimpleNamespace(publish=odometry.append)
        node.tf_broadcaster = SimpleNamespace(sendTransform=transforms.append)
        node.on_timer()
        msg, tf = odometry[0], transforms[0]
        omega = node.speed_mps / node.radius_m
        yaw = omega * seconds + math.pi / 2
        body_velocity = msg.twist.twist.linear
        world_x = math.cos(yaw) * body_velocity.x - math.sin(yaw) * body_velocity.y
        world_y = math.sin(yaw) * body_velocity.x + math.cos(yaw) * body_velocity.y
        assert world_x == pytest.approx(-node.speed_mps * math.sin(omega * seconds), abs=1e-12)
        assert world_y == pytest.approx(node.speed_mps * math.cos(omega * seconds), abs=1e-12)
        expected_z = .5 * omega * node.vertical_wave_m * math.cos(.5 * omega * seconds)
        assert body_velocity.z == pytest.approx(expected_z)
        assert msg.twist.twist.angular.z == pytest.approx(omega)
        assert tf.header == msg.header
        assert tf.child_frame_id == msg.child_frame_id == 'uav/base_link'
        assert tf.transform.translation.x == msg.pose.pose.position.x
        assert tf.transform.translation.y == msg.pose.pose.position.y
        assert tf.transform.translation.z == msg.pose.pose.position.z
        assert tf.transform.rotation == msg.pose.pose.orientation
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
