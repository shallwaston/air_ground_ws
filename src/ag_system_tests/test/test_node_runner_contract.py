"""R1 host-only contracts for the actual runner, with controlled rclpy doubles.

These tests execute Python ownership, dispatch and exception paths. They do not
validate Jazzy native handles, native signal threads, DDS or ROS entrypoints.
The installed-console/native-signal suite in ag_system_tests remains required.
"""

import ast
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'src/ag_network_tools/ag_network_tools/node_runner.py'


def entrypoints():
    result = []
    for setup in sorted((ROOT / 'src').glob('*/setup.py')):
        for item in ast.walk(ast.parse(setup.read_text())):
            if isinstance(item, ast.keyword) and item.arg == 'entry_points':
                for entry in ast.literal_eval(item.value).get('console_scripts', []):
                    name, destination = entry.split('=', 1)
                    module, function = destination.strip().split(':')
                    path = setup.parent / (module.replace('.', '/') + '.py')
                    tree = ast.parse(path.read_text())
                    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                                and n.name == function)
                    result.append((name.strip(), path, main))
    return result


ENTRIES = entrypoints()


@contextmanager
def environment():
    """Load the production file without replacing its canonical import name."""
    state = SimpleNamespace(events=[], contexts=[], nodes=[], executors=[],
                            fail=None, primary=ValueError('business failure'),
                            cleanup_fail=set(), callback=None, stop_phase=None,
                            stop_pattern=(), runner=None, native_options=0)

    def checkpoint(phase, context):
        if state.stop_phase == phase:
            for number in state.stop_pattern:
                was_valid = context.ok()
                os.kill(os.getpid(), number)
                assert context.ok() == was_valid

    class Context:
        def __init__(self):
            self.alive = False
            state.contexts.append(self)

        def ok(self):
            return self.alive

        def try_shutdown(self):
            state.events.append('context')
            checkpoint('context-shutdown', self)
            if 'context' in state.cleanup_fail:
                raise RuntimeError('context cleanup failure')
            self.alive = False

    class Handle:
        destroyed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def destroy_when_not_in_use(self):
            self.destroyed = True

    class Guard:
        destroyed = False

        def destroy(self):
            self.destroyed = True
            state.events.append('guard')

    class Node:
        def __init__(self, *, context):
            assert context is state.contexts[-1]
            self.context = context
            self._Node__node = Handle()
            self._publishers = [object()]
            state.nodes.append(self)
            checkpoint('node-init', context)
            if state.fail == 'node-base':
                raise state.primary
            self._type_description_service = None
            if state.fail == 'constructor':
                raise state.primary

        def destroy_publisher(self, entity):
            self._publishers.remove(entity)

        def destroy_node(self):
            state.events.append('node')
            checkpoint('node-destroy', self.context)
            if 'node-before' in state.cleanup_fail:
                raise RuntimeError('node cleanup failure')
            self._publishers.clear()
            self._Node__node.destroy_when_not_in_use()
            if 'node-after' in state.cleanup_fail:
                raise RuntimeError('node cleanup failure')

    class Executor:
        def __init__(self, *, context):
            self.context = context
            self._guard = Guard()
            state.executors.append(self)
            checkpoint('executor-init', context)
            if state.fail == 'executor':
                raise state.primary

        def add_node(self, node):
            assert self.context is node.context
            self.node = node

        def spin_once(self, *, timeout_sec):
            assert timeout_sec > 0
            assert self.context is self.node.context
            checkpoint('spin', self.context)
            if state.callback is not None:
                state.callback(self.node)
            elif not self.context.stop_requested:
                state.runner.request_stop(self.node)

        def shutdown(self):
            state.events.append('executor')
            if 'executor' in state.cleanup_fail:
                raise RuntimeError('executor cleanup failure')
            return 'executor-false' not in state.cleanup_fail

    rclpy = ModuleType('rclpy')

    def initialize(*, args, context, signal_handler_options):
        assert args == [] and signal_handler_options == 0
        checkpoint('context-init', context)
        if state.fail == 'context-before':
            raise state.primary
        context.alive = True
        if state.fail == 'context-after':
            raise state.primary

    def forbidden_global(*args, **kwargs):
        raise AssertionError('managed run accessed a default Context/Executor')

    rclpy.init = initialize
    rclpy.get_default_context = forbidden_global
    rclpy.get_global_executor = forbidden_global
    rclpy.spin = forbidden_global
    rclpy.spin_once = forbidden_global
    modules = {'rclpy': rclpy}
    for name, attributes in {
        'context': {'Context': Context},
        'node': {'Node': Node},
        'executors': {'SingleThreadedExecutor': Executor},
        'exceptions': {'InvalidHandle': type('InvalidHandle', (RuntimeError,), {})},
        'signals': {
            'SignalHandlerOptions': SimpleNamespace(NO=0),
            'get_current_signal_handlers_options': lambda: state.native_options,
            'uninstall_signal_handlers': lambda: None,
            'install_signal_handlers': lambda options: None,
        },
    }.items():
        module = ModuleType('rclpy.' + name)
        module.__dict__.update(attributes)
        modules[module.__name__] = module
    previous = {number: signal.getsignal(number)
                for number in (signal.SIGINT, signal.SIGTERM)}
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location('_r1_runner_under_test', RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        state.runner, state.Node, state.Executor = runner, Node, Executor
        try:
            yield state
        finally:
            assert {number: signal.getsignal(number) for number in previous} == previous


@pytest.fixture
def owned():
    with environment() as state:
        yield state


def leaves(error):
    if isinstance(error, BaseExceptionGroup):
        return [leaf for child in error.exceptions for leaf in leaves(child)]
    return [error]


def test_private_ownership_cleanup_order_and_repeated_runs(owned):
    for _ in range(2):
        owned.runner.run_node(owned.Node, [])
    assert owned.events == ['executor', 'node', 'context'] * 2
    assert len(owned.contexts) == 2 and owned.contexts[0] is not owned.contexts[1]
    assert all(not context.ok() for context in owned.contexts)
    assert all(node._Node__node.destroyed for node in owned.nodes)


def test_repeated_stop_requests_do_not_close_a_running_callback(owned):
    def callback(node):
        for _ in range(5):
            owned.runner.request_stop(node)
            assert node.context.ok()
    owned.callback = callback
    owned.runner.run_node(owned.Node, [])
    assert owned.events == ['executor', 'node', 'context']


def test_already_closed_context_is_safe_to_clean_again(owned):
    owned.callback = lambda node: node.context.try_shutdown()
    owned.runner.run_node(owned.Node, [])
    owned.contexts[0].try_shutdown()
    assert not owned.contexts[0].ok()
    assert owned.nodes[0]._Node__node.destroyed


@pytest.mark.parametrize('phase', ['context-before', 'context-after', 'executor',
                                 'node-base', 'constructor', 'callback'])
def test_partial_initialization_and_business_exceptions_propagate(owned, phase):
    owned.fail = phase
    if phase == 'callback':
        def fail(node):
            raise owned.primary
        owned.callback = fail
    with pytest.raises(ValueError) as caught:
        owned.runner.run_node(owned.Node, [])
    assert caught.value is owned.primary and caught.value.__traceback__ is not None
    assert not owned.contexts[0].ok()
    assert all(node._Node__node.destroyed for node in owned.nodes)
    if phase == 'executor':
        assert owned.executors[0]._guard is None
        assert owned.events == ['guard', 'context']


@pytest.mark.parametrize('closed', [False, True], ids=['valid-context', 'closed-context'])
def test_ros_style_callback_error_is_never_suppressed(owned, closed):
    class SimulatedRCLError(RuntimeError):
        pass
    error = SimulatedRCLError('callback RCL failure')
    def fail(node):
        if closed:
            node.context.try_shutdown()
        raise error
    owned.callback = fail
    with pytest.raises(SimulatedRCLError) as caught:
        owned.runner.run_node(owned.Node, [])
    assert caught.value is error and not owned.contexts[0].ok()


@pytest.mark.parametrize('phase', ['executor', 'executor-false', 'node-before',
                                 'node-after', 'context'])
@pytest.mark.parametrize('business_error', [False, True], ids=['cleanup-only', 'business-and-cleanup'])
def test_cleanup_failures_remain_observable_and_preserve_business_error(owned, phase, business_error):
    owned.cleanup_fail.add(phase)
    if business_error:
        def fail(node):
            raise owned.primary
        owned.callback = fail
    with pytest.raises(BaseExceptionGroup) as caught:
        owned.runner.run_node(owned.Node, [])
    errors = leaves(caught.value)
    assert any(isinstance(error, RuntimeError) for error in errors)
    assert any(error is owned.primary for error in errors) == business_error
    if business_error:
        assert errors[0] is owned.primary and errors[0].__traceback__ is not None
    assert owned.events == ['executor', 'node', 'context']
    assert owned.nodes[0]._Node__node.destroyed
    assert not owned.contexts[0].ok() or phase == 'context'


def test_all_cleanup_failures_and_original_error_are_retained(owned):
    owned.cleanup_fail.update(['executor', 'node-before', 'context'])
    def fail(node):
        raise owned.primary
    owned.callback = fail
    with pytest.raises(BaseExceptionGroup) as caught:
        owned.runner.run_node(owned.Node, [])
    errors = leaves(caught.value)
    assert errors[0] is owned.primary and len(errors) == 4
    assert owned.nodes[0]._Node__node.destroyed
    assert owned.events == ['executor', 'node', 'context']


@pytest.mark.parametrize('phase', ['context-init', 'executor-init', 'node-init',
                                 'spin', 'node-destroy', 'context-shutdown'])
@pytest.mark.parametrize('pattern', [(signal.SIGINT,), (signal.SIGTERM,),
                                   (signal.SIGINT, signal.SIGTERM, signal.SIGINT)],
                         ids=['int', 'term', 'mixed'])
def test_python_signal_stop_is_cooperative_at_owned_phases(phase, pattern):
    # Start a fresh interpreter so real ROS tests in the parent cannot retain
    # native handlers/Contexts while these controlled Python signals are sent.
    # Native rclpy signal operations remain doubles; this is not an S1 proof.
    child = subprocess.run(
        [sys.executable, '-B', str(Path(__file__)), 'signal-case', phase,
         *[str(int(number)) for number in pattern]],
        capture_output=True, text=True, timeout=10)
    print(json.dumps({'signal_phase': phase, 'signals': [int(number) for number in pattern],
                      'actual_exit_code': child.returncode,
                      'stdout': child.stdout, 'stderr': child.stderr}))
    assert child.returncode == 0, child.stderr
    report = json.loads(child.stdout)
    assert report['closed'] and report['nodes_destroyed']
    assert 'Traceback' not in child.stderr


@pytest.mark.parametrize('entry', ENTRIES, ids=[entry[0] for entry in ENTRIES])
@pytest.mark.parametrize('business_error', [False, True], ids=['stop', 'exception'])
def test_actual_main_dispatch_uses_runner_contract(owned, entry, business_error):
    _, path, main = entry
    assert len(ENTRIES) == 21
    assert len(main.body) == 1 and isinstance(main.body[0], ast.Expr)
    call = main.body[0].value
    assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    assert call.func.id == 'run_node' and isinstance(call.args[0], ast.Name)
    namespace = {'run_node': owned.runner.run_node, call.args[0].id: owned.Node}
    module = ast.Module(body=[main], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    if business_error:
        def fail(node):
            raise owned.primary
        owned.callback = fail
        with pytest.raises(ValueError) as caught:
            namespace['main']([])
        assert caught.value is owned.primary
    else:
        namespace['main']([])
    assert owned.events == ['executor', 'node', 'context']
    assert not owned.contexts[0].ok()


def test_worker_thread_rejection_has_no_allocated_resources(owned):
    errors = []
    def attempt():
        try:
            owned.runner.run_node(owned.Node, [])
        except RuntimeError as error:
            errors.append(error)
    worker = threading.Thread(target=attempt)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive() and len(errors) == 1
    assert owned.contexts == []


@pytest.mark.parametrize('invalid', [object, lambda: None], ids=['non-node-class', 'factory'])
def test_invalid_factory_is_rejected_before_ownership(owned, invalid):
    with pytest.raises(TypeError):
        owned.runner.run_node(invalid, [])
    assert owned.contexts == []


@pytest.mark.parametrize('mode,code', [('normal', 0), ('business', 1),
                                    ('cleanup', 1), ('business-cleanup', 1)])
def test_uncaught_child_exit_code_and_traceback(mode, code):
    child = subprocess.run([sys.executable, '-B', str(Path(__file__)), mode],
                           capture_output=True, text=True, timeout=10)
    print(json.dumps({'child_mode': mode, 'actual_exit_code': child.returncode,
                      'stdout': child.stdout, 'stderr': child.stderr}))
    assert child.returncode == code, child.stderr
    report = json.loads(child.stdout)
    assert report['events'] == ['executor', 'node', 'context']
    assert report['closed'] or 'cleanup' in mode
    if 'business' in mode:
        assert 'ValueError: business failure' in child.stderr
    if 'cleanup' in mode:
        assert 'context cleanup failure' in child.stderr
    assert ('Traceback' in child.stderr) == (code != 0)


if __name__ == '__main__':
    with environment() as child_state:
        mode = sys.argv[1]
        if mode == 'signal-case':
            child_state.stop_phase = sys.argv[2]
            child_state.stop_pattern = tuple(int(number) for number in sys.argv[3:])
        if 'business' in mode:
            def fail(node):
                raise child_state.primary
            child_state.callback = fail
        if 'cleanup' in mode:
            child_state.cleanup_fail.add('context')
        try:
            child_state.runner.run_node(child_state.Node, [])
        finally:
            print(json.dumps({'events': child_state.events,
                              'closed': not child_state.contexts[0].ok(),
                              'nodes_destroyed': all(node._Node__node.destroyed
                                                     for node in child_state.nodes)}))
