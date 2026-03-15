# Stage2 Evidence Snapshot

- timestamp: 20260315_221927
- hostname: shallwastonPC
- stage2_machine_role: unset
- env_file: not_provided
- output_dir: /home/shallwaston/air_ground_ws/artifacts/stage2_runs/single_machine_baseline_check
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
ros2 topic echo /uav/targets/current --once FAILED(rc=124) -> uav_targets_current_once.txt
ros2 topic hz /uav/odom      OK -> uav_odom_hz.txt
ros2 topic bw /uav/map/tile  OK -> uav_map_tile_bw.txt
```

## Suggested Acceptance References

- env summary: `single_machine_baseline_check/ros_env_summary.txt`
- topic list: `single_machine_baseline_check/ros2_topic_list.txt`
- node list: `single_machine_baseline_check/ros2_node_list.txt`
- full status: `single_machine_baseline_check/capture_status.txt`
