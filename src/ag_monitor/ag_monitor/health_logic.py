"""Clock-independent liveness calculations used by system_monitor.

Incoming messages use ROS timestamps for data semantics, but wall-clock
liveness must keep working even when simulation time is paused or reset.
"""

from __future__ import annotations

from typing import Mapping


def age_seconds(last_seen_ns: int, now_ns: int) -> float:
    """Return a nonnegative elapsed duration for monotonic timestamps."""
    return max(0.0, (now_ns - last_seen_ns) / 1_000_000_000.0)


def expired_heartbeat_names(
    last_seen_by_node_ns: Mapping[str, int], now_ns: int, timeout_sec: float
) -> list[str]:
    """Identify nodes whose most recent received heartbeat has timed out."""
    return [
        node_name
        for node_name, last_seen_ns in last_seen_by_node_ns.items()
        if age_seconds(last_seen_ns, now_ns) > timeout_sec
    ]
