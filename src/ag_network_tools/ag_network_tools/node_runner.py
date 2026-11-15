"""Own the complete lifecycle of synchronous Jazzy console nodes."""

from __future__ import annotations

from contextlib import contextmanager
import signal
import threading

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.exceptions import InvalidHandle
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.signals import get_current_signal_handlers_options
from rclpy.signals import install_signal_handlers, uninstall_signal_handlers


class _RunContext(Context):
    """A stop request is independent of the validity of ROS resources."""

    stop_requested = False

    def request_stop(self) -> None:
        # No locks, ROS calls, logging, exceptions, or resource teardown in a
        # Python signal handler. Repeated signals simply store the same value.
        self.stop_requested = True


_signal_owner = None


@contextmanager
def _stop_signals(context: _RunContext):
    """Retain every failure while unwinding this synchronous signal scope.

    This is not a process-wide ownership protocol. Unknown native handlers or
    concurrently changing signal owners remain outside the supported boundary.
    """
    global _signal_owner
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('signal scope requires the main thread')
    if _signal_owner is not None:
        raise RuntimeError('nested run_node signal ownership is unsupported')
    _signal_owner = context
    signals = (signal.SIGINT, signal.SIGTERM)
    previous = {}
    native_options = None
    incoming_mask = None
    attempted = []
    native_attempted = False
    failure = None
    errors = []
    entered = False

    def request_stop(signum, frame):
        context.request_stop()

    def attempt(function, *args):
        try:
            return function(*args)
        except BaseException as exc:
            errors.append(exc)
            return None

    try:
        try:
            previous = {number: signal.getsignal(number) for number in signals}
            native_options = get_current_signal_handlers_options()
            # Capture the old mask before a mutating operation can fail after
            # taking effect. An empty set only queries this thread's mask.
            incoming_mask = signal.pthread_sigmask(signal.SIG_BLOCK, ())
            try:
                signal.pthread_sigmask(signal.SIG_BLOCK, signals)
                native_attempted = True
                uninstall_signal_handlers()
                for number in signals:
                    # Register a rollback before the potentially mutating call.
                    attempted.append(number)
                    signal.signal(number, request_stop)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, incoming_mask)
            entered = True
            yield
        except BaseException as exc:
            failure = exc
        finally:
            if incoming_mask is not None:
                # Preserve intentional mask changes made by the body, as the
                # previous implementation did, without losing the entry mask
                # if acquiring the teardown mask itself fails.
                exit_mask = attempt(signal.pthread_sigmask, signal.SIG_BLOCK, ())
                if exit_mask is None or not entered:
                    exit_mask = incoming_mask
                attempt(signal.pthread_sigmask, signal.SIG_BLOCK, signals)
                conflict = False
                if native_attempted:
                    current_native = attempt(get_current_signal_handlers_options)
                    if current_native not in (None, SignalHandlerOptions.NO):
                        conflict = True
                        errors.append(RuntimeError('native signal ownership changed during run_node'))
                    if not conflict:
                        attempt(uninstall_signal_handlers)
                    for number in attempted:
                        current = attempt(signal.getsignal, number)
                        if current is request_stop:
                            attempt(signal.signal, number, previous[number])
                        elif current != previous[number]:
                            conflict = True
                            errors.append(RuntimeError('Python signal ownership changed during run_node'))
                    if not conflict and native_options != SignalHandlerOptions.NO:
                        attempt(install_signal_handlers, native_options)
                attempt(signal.pthread_sigmask, signal.SIG_SETMASK, exit_mask)
    finally:
        # A failed restore retains this scope's ownership: subsequent calls
        # must refuse, rather than acquiring a process with uncertain state.
        _signal_owner = context if errors else None
    if errors:
        if failure is not None:
            errors.insert(0, failure)
        raise BaseExceptionGroup('signal scope cleanup failed', errors)
    if failure is not None:
        raise failure.with_traceback(failure.__traceback__)


def request_stop(node: Node) -> None:
    """Finish a managed one-shot without invalidating an executing callback.

    Directly instantiated nodes outside run_node retain their previous context
    shutdown behavior. Console entrypoints always use the cooperative context.
    """
    if isinstance(node.context, _RunContext):
        node.context.request_stop()
    elif node.context is rclpy.get_default_context():
        # Preserve rclpy.try_shutdown's default-context reset for legacy users.
        rclpy.try_shutdown()
    else:
        node.context.try_shutdown()


def _destroy_node(node: Node) -> None:
    errors = []
    if hasattr(node, '_type_description_service'):
        try:
            node.destroy_node()
            return
        except BaseException as exc:
            # A failing custom destructor must not strand the remaining
            # entities, nor hide a business exception already in flight.
            errors.append(exc)
    # Jazzy Node.__init__ may fail after creating the C node/parameter publisher
    # but before installing TypeDescriptionService. Its destroy_node assumes
    # that final attribute exists. Release only resources actually allocated.
    for name, destroy in (
        ('_publishers', 'destroy_publisher'), ('_subscriptions', 'destroy_subscription'),
        ('_clients', 'destroy_client'), ('_services', 'destroy_service'),
        ('_timers', 'destroy_timer'), ('_guards', 'destroy_guard_condition'),
    ):
        for entity in list(getattr(node, name, ())):
            try:
                getattr(node, destroy)(entity)
            except BaseException as exc:
                errors.append(exc)
    description_service = getattr(node, '_type_description_service', None)
    if description_service is not None:
        try:
            description_service.destroy()
        except BaseException as exc:
            errors.append(exc)
    handle = getattr(node, '_Node__node', None)
    if handle is not None:
        try:
            with handle:
                handle.destroy_when_not_in_use()
        except InvalidHandle:
            pass  # Already released by the custom destructor.
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise BaseExceptionGroup('node resource cleanup failed', errors)


def run_node(node_type: type[Node], args: list[str] | None = None) -> None:
    """Run one Node class with an explicit Context and single-threaded Executor.

    Node constructors accept context= and retain their no-argument API. Allocate
    before __init__ so even a partially constructed node has an owned cleanup
    path. Current console nodes use synchronous callbacks: after spin_once
    returns, no callback is executing on another thread. An idle bounded wait
    observes stop requests without unsafe ROS calls from the signal handler.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('run_node must run on the main thread to manage signals')
    if not isinstance(node_type, type) or not issubclass(node_type, Node):
        raise TypeError('run_node requires a Node class accepting context=')

    if _signal_owner is not None:
        raise RuntimeError('nested run_node signal ownership is unsupported')

    context = _RunContext()
    node = None
    executor = None
    executor_ready = False
    failure = None
    with _stop_signals(context):
        try:
            rclpy.init(args=args, context=context, signal_handler_options=SignalHandlerOptions.NO)
            if context.stop_requested:
                return
            # Seed the fields read by Jazzy Executor.__del__, and retain ownership
            # if a real allocation failure interrupts Executor.__init__.
            executor = SingleThreadedExecutor.__new__(SingleThreadedExecutor)
            executor._guard = None
            executor._sigint_gc = None
            SingleThreadedExecutor.__init__(executor, context=context)
            executor_ready = True
            if context.stop_requested:
                return
            node = node_type.__new__(node_type)
            node._Node__executor_weakref = None
            node_type.__init__(node, context=context)
            if context.stop_requested:
                return
            executor.add_node(node)
            while not context.stop_requested and context.ok():
                executor.spin_once(timeout_sec=0.1)
        except BaseException as exc:
            failure = exc
            raise
        finally:
            errors = []
            if executor is not None:
                if executor_ready:
                    try:
                        if not executor.shutdown():
                            raise RuntimeError('executor did not finish shutdown')
                    except BaseException as exc:
                        errors.append(exc)
                else:
                    for name in ('_guard', '_sigint_gc'):
                        guard = getattr(executor, name, None)
                        if guard is not None:
                            try:
                                guard.destroy()
                            except BaseException as exc:
                                errors.append(exc)
                            else:
                                setattr(executor, name, None)
            if node is not None:
                try:
                    _destroy_node(node)
                except BaseException as exc:
                    errors.append(exc)
            try:
                context.try_shutdown()
            except BaseException as exc:
                errors.append(exc)
            if errors:
                if failure is not None:
                    errors.insert(0, failure)
                raise BaseExceptionGroup('node lifecycle cleanup failed', errors)
