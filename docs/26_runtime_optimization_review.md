# ROS 2 Jazzy runtime optimization review

Base: `e129564eb5de9125209600f63e4112a85338c02f` (master).
Reviewed PR #2 at `e63cfd28535e14e080996df4283020f96d1faedd`.
Validation: Ubuntu 24.04, ROS 2 Jazzy / Fast DDS, Python 3.12.3, local discovery.

## Findings and changes

| Area | Finding | Resolution |
| --- | --- | --- |
| All 21 console nodes | Signal handling may already have shut down the context before unconditional `rclpy.shutdown()`; initialization failures also escaped cleanup | Shared `run_node` destroys nodes and uses idempotent shutdown. Handles normal interruption and the Jazzy executor wait-set race in a closed context, while propagating real constructor/callback failures |
| PR #2 report QoS | Three report endpoints used heartbeat policy | Retained the PR's fix to look up `/system/delay_report`; tested with distinct heartbeat/report profiles |
| PR #2 liveness | Arrival times used monotonic time but summary time still used ROS time; `expired_heartbeat_names` was imported but never called | Use monotonic time consistently; warn and remove stale per-node entries |
| Monitor timer | ROS-time summary timer never fires when simulation time is paused, even if age calculations use monotonic time | Explicit steady-clock timer; regression holds ROS time at zero and verifies real timer-driven expiry |
| Launch QoS | `qos_config` only configured the inspector, not the publishers/subscribers | Propagate `AG_QOS_CONFIG_PATH` to launched children; explicit paths override the environment, then packaged/default lookup applies. Does not dynamically recreate existing endpoints |
| QoS loading | Repeated YAML parsing, partial overrides discarded default fields, invalid enum spellings silently selected different policies | Cache by resolved path/mtime/size, return private copies, merge partial profiles, reject invalid policies/depths and explicit missing paths |
| PR #2 map math | Row/column precomputation preserves the exact legacy per-cell expression | Retained; compare every cell and traversal value across rectangular, 256x256, negative-phase and long-running-phase inputs |
| TF | Three duplicate quaternion implementations; constant alignment rotation recomputed at 10 Hz; static broadcaster bypassed configured QoS | Shared quaternion utility and explicit dependency; compute constant alignment rotation once; use `/tf_static` policy |
| Static TF input | Empty/self/duplicate child frames, local cycles and nonfinite coordinates could be broadcast | Validate before broadcasting; retain missing-file warning behavior |
| Mock Odometry | World-frame linear velocity was placed in child-frame twist; vertical derivative had the wrong factor | Body-frame forward velocity and analytical vertical derivative; preserve pose, TF, message definitions, frame names and publish frequency |
| Target timestamps | Position phase and header used two clock reads | Use one ROS time sample per message |
| Topic watchdog | Allocated full endpoint descriptions just to count them | Use ROS count APIs |
| Tests/manifests | Original suite had 8 tests and did not check clean console shutdown or live data | Add signal, startup/callback error, paused-clock, QoS, TF, odometry, late-joiner and full graph integration tests; declare direct test dependencies |
| Interface package discovery | Empty `<export/>` made colcon identify `ag_interfaces` as catkin; Python imports worked but its prefix was missing from the ament search path and rosbag rejected its types | Declare `ament_cmake`, regenerate this package's build outputs, and test ament package/interface registration |

## Compatibility

No `.msg` files, topic constants, frame names, launch filenames/arguments, existing
console entrypoints, default QoS YAML policies or default publication frequencies
changed. Imported quaternion functions remain available in their original modules.
Both QoS YAML copies and built-in defaults are checked for equality.

Intentional behavior corrections: invalid QoS/TF input now fails clearly instead
of silently selecting another policy or broadcasting corrupt TF; partial QoS
overrides retain defaults; launch overrides now affect actual communication;
heartbeat counts expire; Odometry twist follows `child_frame_id` conventions.
ROS timestamps remain ROS time, distinct from arrival liveness time.

If upgrading a workspace already built before the interface-package fix, remove
only its generated `build/ag_interfaces` and `install/ag_interfaces` directories
before rebuilding. Old catkin-generated directories conflict with ament's Python
symlinks. Source the new `install/setup.bash` after rebuilding. A fresh checkout
does not need this cleanup.

## Actual validation

Each implementation group was built and checked before proceeding. Final run:

```bash
source /opt/ros/jazzy/setup.bash
./scripts/build_ws.sh --parallel-workers 2
source install/setup.bash
python3 -m pytest -q src/ag_system_tests/test
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
```

- Build: all 7 packages succeeded.
- Direct pytest: **98 passed**.
- Full workspace colcon: **98 tests, 0 errors, 0 failures, 0 skipped**.
  Tests live in `ag_system_tests`; the other packages do not have independent suites.
- 21 console entrypoints each start and exit with code 0 for both SIGINT and
  SIGTERM. Constructor/callback defects still propagate. DDS probe names are
  unique so stale discovery records cannot make a later test signal too early.
- All six launch descriptions load; heartbeat launch smoke passes.
- The complete single-machine launch sends all six monitored message/report
  types, valid map arrays and all three key TF chains. A custom best-effort map
  policy is visible on actual DDS endpoints. SIGINT stops the launch without
  tracebacks or failed node exits.
- A one-shot transient-local map publication is received by a later subscriber.
- A separate default single-machine smoke also passes after the full suite.
- Supplemental integration in ROS domain 43: the default stress launch produced
  valid 256x256 map arrays and delay probes. SQLite rosbag recording captured
  **17 map tiles and 13 delay probes**; playback delivered **all 30 messages** to
  real subscribers. This initially failed on the missing interface-package
  registration described above and passed after the package metadata fix.
- `future_adapters_stub.launch.py` started all six adapter stubs and stopped
  without tracebacks or failed node exits. No real hardware was involved.

The supplemental workflow uses `ros2 launch ag_bringup qos_stress_test.launch.py`,
`ros2 bag record -s sqlite3 -o <new-bag> --topics /uav/map/tile /system/delay_probe`,
then stops publishers and runs `ros2 bag play <new-bag> --delay 1` while subscribing
to both recorded types. These are additional checks, not part of the pytest count.

In the managed cloud host, run ROS commands through
`/workspace/.air-ground-env/ros`, for example:

```bash
/workspace/.air-ground-env/ros python3 -m pytest -q src/ag_system_tests/test
```

## Reproducible performance measurement

```bash
python3 scripts/benchmark_mock_tile.py
```

The script reads the original publisher from the fixed baseline commit without
changing branches. It compares identical dimensions and phases, then times real
publisher callbacks, including message construction and ROS publication with
**no subscribers**. Seven repetitions, medians; 100 calls per 64x64 repetition,
10 per 256x256 repetition. Pure layer measurements are reported separately.
See `benchmarks/jazzy_map_results.json` for measured results.

| Map size | Legacy callback median | Optimized callback median | Reduction |
| --- | --- | --- | --- |
| 64x64 | 1.212 ms | 0.566 ms | 53.3% |
| 256x256 | 18.277 ms | 11.357 ms | 37.9% |

Measured after the final suites and supplemental integration had finished, with
no other ROS application graph running in this container.

These numbers describe local computation/callback cost. They do not establish
network throughput, distributed latency, process CPU utilization, hardware
performance or higher output frequency; the configured frequencies are unchanged.

## Remaining limits

- No two physical machines, VPN/DDS Discovery Server failover, Wi-Fi, netem,
  chrony synchronization, Jetson or real sensor/arm/Nav2/FAST-LIO2 hardware was
  tested. Launch-description checks and adapter stubs are not hardware evidence.
- Recorded ROS timestamps and replay wall time are different; do not interpret
  replay delay reports as network latency. The existing replay launch's clock
  configuration and real synchronized-clock testing need separate work.
- The QoS cache detects normal file edits by path/mtime/size. Existing endpoints
  require node restart after policy changes; dynamic QoS reconfiguration is not
  implemented.
- Local invalid-TF checks cannot detect conflicting publishers or cycles formed
  by independent external TF broadcasters.
- Graceful shutdown's narrow wait-set exception handling targets the installed
  Jazzy executor; retain the signal tests when upgrading ROS.

## Modified files

All node mains in `ag_mock_nodes`, `ag_monitor` and `ag_tf_tools` use the shared
lifecycle helper. Main functional edits are:

- `ag_network_tools/node_runner.py`, `qos_profiles.py`, `transforms.py`, and its package manifest.
- `ag_monitor/system_monitor.py`, `topic_watchdog.py`, `delay_probe_sub.py`, plus PR #2's `health_logic.py`.
- `ag_mock_nodes/uav_mock_map_tile_pub.py`, `mock_tile_math.py`, `ugv_map_tile_sub.py`, `uav_mock_odom_tf_pub.py`, `uav_mock_target_pub.py`.
- `ag_tf_tools/frame_alignment_stub.py`, `static_tf_loader.py`, `tf_healthcheck.py`.
- Five launch files with a `qos_config` argument.
- `ag_system_tests` manifest, expanded launch tests, and added shutdown, runtime,
  map-math, odometry and single-machine integration tests.
- `ag_interfaces/package.xml` explicitly selects `ament_cmake`; message definitions are unchanged.
- `scripts/benchmark_mock_tile.py`, this review, the PR #2 review follow-up and raw benchmark results.
