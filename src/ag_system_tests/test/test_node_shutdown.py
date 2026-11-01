"""Exercise actual Jazzy signal handlers on every installed console node."""

import importlib.metadata
import signal
import subprocess
import sys
import time
import uuid

import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node

from ag_network_tools.node_runner import run_node


ENTRYPOINTS = [
    entry.value.split(':')[0]
    for package in ('ag_mock_nodes', 'ag_monitor', 'ag_tf_tools')
    for entry in importlib.metadata.distribution(package).entry_points
    if entry.group == 'console_scripts'
]


@pytest.mark.parametrize('module', ENTRYPOINTS)
@pytest.mark.parametrize('stop_signal', [signal.SIGINT, signal.SIGTERM])
def test_console_node_stops_cleanly(module, stop_signal, tmp_path):
    context = Context()
    rclpy.init(context=context)
    probe = Node('shutdown_test_probe', context=context)
    unique_name = 'shutdown_' + uuid.uuid4().hex
    with (tmp_path / 'node.log').open('w+') as log:
        process = subprocess.Popen(
            [sys.executable, '-c', f'from {module} import main; main()',
             '--ros-args', '-r', f'__node:={unique_name}'],
            stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 10
            while unique_name not in probe.get_node_names():
                assert process.poll() is None, 'node exited before discovery'
                assert time.monotonic() < deadline, 'node not discovered'
                time.sleep(0.05)
            # Discovery can precede completion of the constructor.
            time.sleep(0.2)
            process.send_signal(stop_signal)
            process.wait(timeout=10)
            log.seek(0)
            output = log.read()
            assert process.returncode == 0, output
            assert 'Traceback' not in output, output
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            probe.destroy_node()
            context.try_shutdown()


def test_constructor_failure_releases_context():
    def fail():
        raise ValueError('invalid startup configuration')

    with pytest.raises(ValueError, match='invalid startup configuration'):
        run_node(fail, args=[])
    assert not rclpy.ok()


def test_callback_failure_is_not_suppressed():
    class BrokenNode(Node):
        def __init__(self):
            super().__init__('broken_callback')
            self.create_timer(0.01, self.fail)

        def fail(self):
            raise ValueError('callback defect')

    with pytest.raises(ValueError, match='callback defect'):
        run_node(BrokenNode, args=[])
    assert not rclpy.ok()
