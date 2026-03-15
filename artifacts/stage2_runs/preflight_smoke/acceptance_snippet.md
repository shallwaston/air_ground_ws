# Stage2 Evidence Snapshot

- timestamp: 20260315_221733
- hostname: shallwastonPC
- stage2_machine_role: unset
- env_file: not_provided
- output_dir: /home/shallwaston/air_ground_ws/artifacts/stage2_runs/preflight_smoke
- workspace_dir: /home/shallwaston/air_ground_ws
- ROS_DOMAIN_ID: unset
- RMW_IMPLEMENTATION: unset
- ROS_DISCOVERY_SERVER: unset
- ROS_LOCALHOST_ONLY: unset

## Capture Status

```text
ros_env_summary              OK -> ros_env_summary.txt
hostname                     OK -> hostname.txt
date                         OK -> date.txt
uname -a                     OK -> uname_a.txt
ip a                         FAILED(rc=1) -> ip_a.txt
ros2 node list               FAILED(rc=1) -> ros2_node_list.txt
ros2 topic list              FAILED(rc=1) -> ros2_topic_list.txt
target_once                  SKIPPED
uav_odom_hz                  SKIPPED
uav_map_tile_bw              SKIPPED
```

## Suggested Acceptance References

- env summary: `preflight_smoke/ros_env_summary.txt`
- topic list: `preflight_smoke/ros2_topic_list.txt`
- node list: `preflight_smoke/ros2_node_list.txt`
- full status: `preflight_smoke/capture_status.txt`
