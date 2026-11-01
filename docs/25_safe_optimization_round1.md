# Safe optimization round 1 (master baseline)

Base: `e129564eb5de9125209600f63e4112a85338c02f`

## Scope

- Correct `/system/delay_report` publisher/subscriber QoS lookups: use `DELAY_REPORT_TOPIC`, not `HEARTBEAT_TOPIC`.
- Liveness in `system_monitor` now uses `time.monotonic_ns()` instead of ROS time. This prevents pause/reset of simulated time from corrupting arrival-based timeouts. Expired heartbeat node entries are pruned.
- The mock tile publisher precomputes row and column terms to remove repeated sine and cosine evaluations while retaining exact original per-cell expression/order.
- Pure functions and regression tests are in `health_logic.py`, `mock_tile_math.py`, and `test_safe_optimization_logic.py`.

## Compatibility boundaries

The following are unchanged: all `.msg` contracts, topic strings, frame names, launch file names, publisher/subscriber types, launch arguments, and default QoS YAML policies. Only internal liveness timing, stale-heartbeat accounting, lookup of the correct QoS entry, and mock tile calculation are affected.

Review follow-up: [runtime optimization review](26_runtime_optimization_review.md) records
the fixes for mixed clocks, missing heartbeat pruning, paused summary timers,
launch QoS propagation, and safe shutdown. The two QoS YAML copies are now checked
for equality by regression tests. Offline-bag timestamp interpretation and
two-machine weak-network behavior still require separate validation.

## Acceptance on Ubuntu 24.04 / ROS 2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
python3 -m pytest -q src/ag_system_tests/test/test_safe_optimization_logic.py
python3 -m pytest -q src/ag_system_tests/test
ros2 launch ag_bringup single_machine_mock.launch.py
```

From another terminal (source the same environment):

```bash
ros2 topic list
ros2 topic hz /uav/odom
ros2 topic hz /uav/map/tile
ros2 topic echo /system/delay_report --once
ros2 topic info -v /system/delay_report
```

Manual liveness test: stop one `heartbeat_pub` and check that `system_monitor` reports a smaller heartbeat count after `timeout_sec`, without changing message delivery on other topics. Repeat with `use_sim_time` paused if available.

Performance: collect baseline and changed-branch `/uav/map/tile` output frequency, CPU usage, and payload measurements under identical test conditions. No ROS runtime speedup is claimed from pure function tests alone.

Rollback: return to master; no message migration needed.
