"""Private strict resources, extracted from reviewed R4 cleanup only.

No signal management/default Context/legacy runner calls belong in this module.
"""
from rclpy.context import Context
from rclpy.exceptions import InvalidHandle
from rclpy.node import Node

class _RunContext(Context):
    """A stop request is independent of the validity of ROS resources."""

    stop_requested = False

    def request_stop(self) -> None:
        # No locks, ROS calls, logging, exceptions, or resource teardown in a
        # Python signal handler. Repeated signals simply store the same value.
        self.stop_requested = True

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

def request_stop(node):
    """Only the strict private context can be stopped; never borrow globals."""
    if not isinstance(node.context,_RunContext):
        raise RuntimeError('strict stop requires the owned private context')
    node.context.request_stop()
