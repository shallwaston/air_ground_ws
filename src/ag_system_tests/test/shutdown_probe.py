"""Subprocess-only instrumentation for deterministic lifecycle tests.

No production hooks/environment switches are required. A pipe gate holds the
selected phase; the parent sends a real signal and then explicitly releases it.
"""

import importlib.metadata
import json
import runpy
import signal
import sys

from ament_index_python.packages import get_package_prefix
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.executors import Executor
from rclpy.guard_condition import GuardCondition
from rclpy.impl.implementation_singleton import rclpy_implementation as impl
from rclpy.node import Node
from rclpy.publisher import Publisher
from std_msgs.msg import String

import ag_network_tools.node_runner as runner


def main(case, entry='-', deliveries='1'):
    entry = None if entry == '-' else entry
    deliveries = int(deliveries)
    handles, contexts, nodes, executors, order, published = [], [], [], [], [], []
    previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    selected = False
    primary = None

    def emit(**data):
        print('PROBE ' + json.dumps(data), flush=True)

    def gate(phase, context, native_wait=False):
        nonlocal selected
        if selected or case != phase:
            return
        selected = True
        emit(phase=phase, valid=context.ok())
        if not native_wait:
            for index in range(deliveries):
                assert sys.stdin.readline().strip() == 'release'
                assert context.stop_requested
                # Context.init-before is the only phase without initialized ROS.
                if phase != 'context-init-before':
                    assert context.ok(), 'signal prematurely closed owned Context'
                emit(signal_ack=index + 1, resumed=phase, valid=context.ok(),
                     requested=context.stop_requested)

    def track(handle):
        handles.append(handle)

    original_context_init = runner._RunContext.init
    def context_init(self, *args, **kwargs):
        contexts.append(self)
        gate('context-init-before', self)
        result = original_context_init(self, *args, **kwargs)
        gate('context-init-after', self)
        if case == 'context-fail-after':
            raise ValueError('context initialization defect')
        return result
    runner._RunContext.init = context_init

    original_guard_init = GuardCondition.__init__
    def guard_init(self, *args, **kwargs):
        result = original_guard_init(self, *args, **kwargs)
        track(self.handle)
        if contexts:
            gate('executor-init', contexts[-1])
        return result
    GuardCondition.__init__ = guard_init

    if case == 'executor-fail':
        import rclpy.executors as executor_module
        def fail_guard(*args, **kwargs):
            raise ValueError('executor initialization defect')
        executor_module.SignalHandlerGuardCondition = fail_guard

    original_executor_init = runner.SingleThreadedExecutor.__init__
    def executor_init(self, *args, **kwargs):
        executors.append(self)
        return original_executor_init(self, *args, **kwargs)
    runner.SingleThreadedExecutor.__init__ = executor_init

    original_shutdown = Executor.shutdown
    def shutdown(self, *args, **kwargs):
        assert not self.is_spinning
        assert self.context.ok() or case == 'callback-rcl-closed'
        result = original_shutdown(self, *args, **kwargs)
        assert result and not self.get_nodes()
        order.append('executor')
        return result
    Executor.shutdown = shutdown

    original_node_init = Node.__init__
    def node_init(self, *args, **kwargs):
        nodes.append(self)
        context = kwargs['context']
        gate('node-init-before', context)
        try:
            result = original_node_init(self, *args, **kwargs)
        finally:
            handle = getattr(self, '_Node__node', None)
            if handle is not None:
                track(handle)
            description = getattr(self, '_type_description_service', None)
            service = getattr(description, '_type_description_srv', None)
            if service is not None:
                track(service)
        gate('node-init-after', context)
        return result
    Node.__init__ = node_init

    for method in ('create_publisher', 'create_subscription', 'create_timer',
                   'create_client', 'create_service', 'create_guard_condition'):
        original = getattr(Node, method)
        def create(self, *args, _original=original, **kwargs):
            entity = _original(self, *args, **kwargs)
            track(entity.handle)
            return entity
        setattr(Node, method, create)

    original_publish = Publisher.publish
    def publish(self, msg):
        result = original_publish(self, msg)
        if contexts and contexts[-1].stop_requested:
            assert contexts[-1].ok()
            published.append(self.topic_name)
        return result
    Publisher.publish = publish

    original_destroy = runner._destroy_node
    def destroy(node):
        assert not any(getattr(e, '_is_spinning', False) for e in executors)
        gate('node-destroy', node.context)
        try:
            return original_destroy(node)
        finally:
            order.append('node')
    runner._destroy_node = destroy

    def open_handles():
        count = 0
        for handle in handles:
            try:
                with handle:
                    count += 1
            except impl.InvalidHandle:
                pass
        return count

    original_try_shutdown = runner._RunContext.try_shutdown
    def try_shutdown(self):
        if case == 'callback-rcl-closed' and self.ok() and not order:
            return original_try_shutdown(self)
        gate('context-shutdown', self)
        # Every node-owned entity and both executor guards must already be gone.
        assert open_handles() == 0
        order.append('context')
        return original_try_shutdown(self)
    runner._RunContext.try_shutdown = try_shutdown

    original_wait_set = impl.WaitSet
    wait_calls = 0
    class CheckedWaitSet(original_wait_set):
        def wait(self, timeout):
            nonlocal wait_calls
            wait_calls += 1
            # Observe entry into native waiting without holding the child in a
            # pipe read: the real wait executes, with no ready user timer.
            if wait_calls >= 2:
                gate('wait', contexts[-1], native_wait=True)
            return super().wait(timeout)
    impl.WaitSet = CheckedWaitSet

    class ProbeNode(Node):
        def __init__(self, *, context):
            super().__init__('lifecycle_probe', context=context)
            self.pub = self.create_publisher(String, '/lifecycle_probe', 1)
            self.sub = self.create_subscription(String, '/lifecycle_probe', lambda msg: None, 1)
            if case == 'constructor-fail':
                self.create_timer(1., lambda: None)
                raise ValueError('constructor business defect')
            self.create_timer(3600. if case == 'wait' else .001, self.tick)

        def tick(self):
            gate('timer', self.context)
            if case in ('callback-fail', 'cleanup-fail', 'cleanup-fail-before'):
                raise ValueError('callback business defect')
            if case in ('callback-rcl', 'callback-rcl-closed'):
                if case == 'callback-rcl-closed':
                    self.context.try_shutdown()
                raise impl.RCLError('callback RCL business defect')
            self.pub.publish(String(data='callback completed with valid context'))
            runner.request_stop(self)

        def destroy_node(self):
            if case == 'cleanup-fail-before':
                raise RuntimeError('cleanup before release defect')
            result = super().destroy_node()
            if case == 'cleanup-fail':
                raise RuntimeError('cleanup defect')
            return result

    if case == 'node-base-fail':
        import rclpy.node as node_module
        def fail_description(*args, **kwargs):
            raise ValueError('base Node initialization defect')
        node_module.TypeDescriptionService = fail_description

    node_type = ProbeNode
    if case == 'map':
        import ag_mock_nodes.uav_mock_map_tile_pub as module
        original_layers = module.build_mock_tile_layers
        def layers(*args, **kwargs):
            gate('map', contexts[-1])
            return original_layers(*args, **kwargs)
        module.build_mock_tile_layers = layers
        node_type = module.UavMockMapTilePub
    if case == 'static-load':
        from ag_tf_tools.static_tf_loader import StaticTfLoader
        original_load = StaticTfLoader.load_transforms
        def load(self, path):
            gate('static-load', self.context)
            return original_load(self, path)
        StaticTfLoader.load_transforms = load
        node_type = StaticTfLoader
    if case == 'entry':
        # Stop each installed executable at its first real executor wait.
        case = 'wait'

    try:
        if entry:
            package, name = entry.split(':')
            executable = Path(get_package_prefix(package)) / 'lib' / package / name
            assert executable.is_file()
            sys.argv = [str(executable)]
            try:
                runpy.run_path(str(executable), run_name='__main__')
            except SystemExit as exc:
                if exc.code not in (None, 0):
                    raise
        else:
            args = ['--ros-args', '--not-a-valid-ros-option'] if case == 'context-fail-before' else []
            runner.run_node(node_type, args=args)
    except BaseException as exc:
        primary = type(exc).__name__
        raise
    finally:
        if selected and case == 'wait':
            assert contexts[-1].stop_requested
        assert all(not c.ok() for c in contexts)
        assert open_handles() == 0
        assert {s: signal.getsignal(s) for s in previous} == previous
        assert signal.pthread_sigmask(signal.SIG_BLOCK, []) == mask
        for node in nodes:
            for field in ('_publishers', '_subscriptions', '_clients', '_services', '_timers', '_guards'):
                assert not getattr(node, field, ())
        if 'node' in order and 'executor' in order:
            assert order.index('executor') < order.index('node')
        if 'node' in order:
            assert order.index('node') < order.index('context')
        emit(clean=True, phase_seen=selected, remaining_handles=open_handles(),
             context_closed=all(not c.ok() for c in contexts),
             python_handlers_restored=True, handles=len(handles), nodes=len(nodes),
             executors=len(executors), order=order, published=published, error=primary)


if __name__ == '__main__':
    main(*sys.argv[1:])
