"""Common lifecycle for console nodes, including signal-driven shutdown."""

from __future__ import annotations

from collections.abc import Callable

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.impl.implementation_singleton import rclpy_implementation
from rclpy.node import Node


def run_node(factory: Callable[[], Node], args: list[str] | None = None) -> None:
    """Destroy the node and close its context exactly once, even on startup failure.

    Jazzy's signal handler may close the context before spin returns. Only normal
    interruption is suppressed; constructor and callback errors still propagate.
    """
    rclpy.init(args=args)
    node = None
    try:
        node = factory()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except rclpy_implementation.RCLError as exc:
        # The signal-handler thread can close the context while the executor is
        # building its wait set. Do not suppress RCL failures in a live context.
        traceback = exc.__traceback__
        while traceback.tb_next is not None:
            traceback = traceback.tb_next
        if rclpy.ok() or traceback.tb_frame.f_code.co_name != '_wait_for_ready_callbacks':
            raise
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            rclpy.try_shutdown()
