"""Real-signal subprocess matrix and installed-console lifecycle regressions."""

import importlib.metadata
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from std_msgs.msg import String

from ag_network_tools.node_runner import request_stop, run_node


PROBE = Path(__file__).with_name('shutdown_probe.py')
ENTRYPOINTS = [
    f'{package}:{entry.name}'
    for package in ('ag_mock_nodes', 'ag_monitor', 'ag_tf_tools')
    for entry in importlib.metadata.distribution(package).entry_points
    if entry.group == 'console_scripts'
]
PHASES = (
    'context-init-before', 'context-init-after', 'executor-init',
    'node-init-before', 'node-init-after', 'wait', 'timer', 'map',
    'static-load', 'node-destroy', 'context-shutdown',
)
REPEATS = int(os.environ.get('AG_SHUTDOWN_STRESS_REPEATS', '3'))
assert REPEATS >= 3, 'the lifecycle matrix requires at least three repetitions'


def run_probe(tmp_path, case, stop_signal=None, entry=None):
    messages = []
    pattern = (tuple(stop_signal) if isinstance(stop_signal, (tuple, list))
               else (stop_signal,) if stop_signal is not None else ())
    command = [sys.executable, str(PROBE), case, entry or '-', str(len(pattern) or 1)]
    with (tmp_path / 'node.log').open('w+') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=log)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        pending = b''
        deadline = time.monotonic() + 20
        signals_sent = 0
        try:
            while True:
                remaining = deadline - time.monotonic()
                assert remaining > 0, f'probe timed out: {case}; messages={messages}'
                events = selector.select(remaining)
                assert events, f'probe produced no event: {case}'
                data = os.read(process.stdout.fileno(), 65536)
                if not data:
                    break
                pending += data
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    if not line.startswith(b'PROBE '):
                        continue
                    message = json.loads(line[6:])
                    messages.append(message)
                    if 'phase' in message:
                        assert pattern and signals_sent == 0
                        if message['phase'] != 'context-init-before':
                            assert message['valid']
                    if ('phase' in message or 'signal_ack' in message) and signals_sent < len(pattern):
                        process.send_signal(pattern[signals_sent])
                        signals_sent += 1
                        if message.get('phase') != 'wait':
                            process.stdin.write(b'release\n')
                            process.stdin.flush()
            process.wait(timeout=10)
            log.seek(0)
            output = log.read()
            clean = [m for m in messages if m.get('clean')]
            assert len(clean) == 1, output
            report = clean[0]
            (tmp_path / 'cleanup.json').write_text(json.dumps({
                'case': case, 'entry': entry, 'signals': [int(s) for s in pattern],
                'exit_code': process.returncode, 'report': report, 'events': messages}, indent=2))
            if stop_signal is not None:
                assert signals_sent == len(pattern) and report['phase_seen'], messages
                assert process.returncode == 0, output
                assert report['error'] is None, output
                for text in ('Traceback', 'context is invalid', 'context is not valid',
                             'failed to create guard_condition', 'Exception ignored in:'):
                    assert text not in output, output
            return process.returncode, output, report
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            selector.close()
            process.stdin.close()
            process.stdout.close()


@pytest.mark.parametrize('repeat', range(REPEATS))
@pytest.mark.parametrize('stop_signal', [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize('phase', PHASES)
def test_signal_timing_matrix(phase, stop_signal, repeat, tmp_path):
    _, _, report = run_probe(tmp_path, phase, stop_signal)
    if phase in ('timer', 'map', 'static-load'):
        expected = {'timer': '/lifecycle_probe', 'map': '/uav/map/tile',
                    'static-load': '/tf_static'}[phase]
        assert expected in report['published'], report
    if phase not in ('context-init-before', 'context-init-after', 'executor-init'):
        assert report['handles'] > 0 and report['nodes'] == 1, report


@pytest.mark.parametrize('entry', ENTRYPOINTS)
@pytest.mark.parametrize('stop_signal', [signal.SIGINT, signal.SIGTERM])
def test_console_node_stops_cleanly(entry, stop_signal, tmp_path):
    _, _, report = run_probe(tmp_path, 'entry', stop_signal, entry)
    assert report['nodes'] == report['executors'] == 1
    assert report['handles'] > 0



@pytest.mark.parametrize('phase', [
    'node-init-before', 'timer', 'map', 'static-load', 'node-destroy', 'context-shutdown',
])
@pytest.mark.parametrize('pattern', [
    (signal.SIGINT,) * 5, (signal.SIGTERM,) * 5,
    (signal.SIGINT, signal.SIGTERM, signal.SIGINT, signal.SIGTERM, signal.SIGTERM),
], ids=['int-burst', 'term-burst', 'mixed-burst'])
def test_repeated_signals_keep_active_context_valid(phase, pattern, tmp_path):
    run_probe(tmp_path, phase, pattern)


def test_installed_entrypoint_set_is_complete():
    assert len(ENTRYPOINTS) == len(set(ENTRYPOINTS)) == 21


@pytest.mark.parametrize('case,description', [
    ('context-fail-before', 'UnknownROSArgsError'),
    ('context-fail-after', 'context initialization defect'),
    ('executor-fail', 'executor initialization defect'),
    ('node-base-fail', 'base Node initialization defect'),
    ('constructor-fail', 'constructor business defect'),
    ('callback-fail', 'callback business defect'),
    ('callback-rcl', 'callback RCL business defect'),
    ('callback-rcl-closed', 'callback RCL business defect'),
    ('cleanup-fail', 'callback business defect'),
    ('cleanup-fail-before', 'callback business defect'),
])
def test_real_failures_propagate_and_release_resources(case, description, tmp_path):
    code, output, report = run_probe(tmp_path, case)
    assert code != 0 and report['error'] is not None
    assert description in output, output
    if case.startswith('cleanup-fail'):
        assert 'cleanup' in output
        assert report['error'] == 'ExceptionGroup'


def test_other_context_and_python_handlers_survive():
    other = Context()
    other.init(args=[])
    node = Node('unrelated_context', context=other)
    pub = node.create_publisher(String, '/unrelated_context', 1)
    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    def unrelated_handler(signum, frame):
        raise AssertionError('runner leaked a signal to the caller handler')
    class OneShot(Node):
        def __init__(self, *, context):
            super().__init__('managed_one_shot', context=context)
            self.create_timer(.001, lambda: request_stop(self))
    try:
        for number in previous:
            signal.signal(number, unrelated_handler)
        run_node(OneShot, args=[])
        assert other.ok()
        pub.publish(String(data='still works'))
        assert all(signal.getsignal(s) is unrelated_handler for s in previous)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
        node.destroy_node()
        other.try_shutdown()


def test_tf_one_shot_uses_managed_stop_request(tmp_path):
    # Preserve the existing one-shot result semantics (M5 is outside this patch),
    # but ensure it stops the owned Context, rather than an unrelated default one.
    process = subprocess.run(
        ['ros2', 'run', 'ag_tf_tools', 'tf_healthcheck', '--ros-args',
         '-p', 'one_shot:=true', '-p', 'check_period_sec:=0.5'],
        capture_output=True, text=True, timeout=15)
    assert process.returncode == 0, process.stderr
    assert 'One-shot TF check complete' in process.stderr + process.stdout
    assert 'Traceback' not in process.stderr + process.stdout


def test_callers_native_signal_layer_is_restored():
    code = '''
import os, signal, time
import rclpy
from rclpy.node import Node
from rclpy.signals import get_current_signal_handlers_options, SignalHandlerOptions, uninstall_signal_handlers
from std_msgs.msg import String
from ag_network_tools.node_runner import request_stop, run_node
rclpy.init(args=[])
other = rclpy.get_default_context()
node = Node('native_signal_caller')
pub = node.create_publisher(String, '/native_signal_caller', 1)
previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
class OneShot(Node):
    def __init__(self, *, context):
        super().__init__('native_restoration_probe', context=context)
        self.create_timer(.001, lambda: request_stop(self))
try:
    assert get_current_signal_handlers_options() == SignalHandlerOptions.ALL
    run_node(OneShot, args=[])
    assert other.ok()
    assert {s: signal.getsignal(s) for s in previous} == previous
    assert get_current_signal_handlers_options() == SignalHandlerOptions.ALL
    pub.publish(String(data='caller survives'))
    os.kill(os.getpid(), signal.SIGTERM)
    # Jazzy native shutdown changes the C++ context but does not invoke the
    # Python Context.on_shutdown list. Observe the actual C++ state instead.
    deadline = time.monotonic() + 5
    while other.ok():
        assert time.monotonic() < deadline, 'original native handler did not receive SIGTERM'
    assert not other.ok()
finally:
    node.destroy_node()
    rclpy.try_shutdown()
    uninstall_signal_handlers()
'''
    process = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15)
    assert process.returncode == 0, process.stderr
    assert 'Traceback' not in process.stderr


def test_direct_stop_keeps_default_context_reinitializable():
    rclpy.init(args=[])
    original = rclpy.get_default_context()
    node = Node('legacy_direct_one_shot')
    try:
        request_stop(node)
        assert not original.ok()
        rclpy.init(args=[])
        assert rclpy.ok()
        assert rclpy.get_default_context() is not original
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
