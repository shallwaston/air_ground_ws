# air_ground_ws

面向 ROS 2 Jazzy + Ubuntu 24.04 的异构空地协同建图与精准抓取系统工程骨架。

当前重点不是直接进入重型真实集成，而是先把通信框架、工程骨架、调试/验收工具链和最小可验证链路搭起来，再逐步接 FAST-LIO2、2.5D 地图、UGV 导航和机械臂抓取。

这个 workspace 当前的目标不是伪造真实硬件驱动，而是先把下面这些最小闭环打通：

- `colcon build --symlink-install` 可构建
- `ros2 launch` 可启动
- 可跑 mock 通信
- 可做 topic/QoS/TF/延迟/带宽诊断
- 可为 FAST-LIO2、2.5D 地图、Nav2、EKF、机械臂等真实模块预留替换点

## 当前状态

当前仓库已具备两条已经收口的单机能力：

- 单机 mock 基线可运行并可验证：`single_machine_mock.launch.py` 已验证 `/uav/odom`、`/uav/map/tile`、`/uav/targets/current`、`/system/delay_probe`、`/tf`、`/tf_static`
- “真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”已打通：`/lidar_points -> pointcloud_to_maptile_adapter -> /uav/map/tile`

当前工程骨架已搭好：

- `ag_interfaces`
- `ag_mock_nodes`
- `ag_monitor`
- `ag_tf_tools`
- `ag_bringup`
- `ag_network_tools`
- `ag_system_tests`

## 当前实验口径

当前实验只能表述为：

`真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验`

不要把当前结果表述为全局融合地图。

## 阶段 4 结论摘要

- 阶段 4 已收口，`R0` 为主锚点基线，阶段 2 结果仅保留为辅助对照
- `R1` 是可信的压缩 trade-off，但不采纳为推荐参数集
- `R2` 是当前阶段 4、当前这条局部 MapTile 实验链路内的默认推荐参数组
- `R3` 是基于 `R2` 的次要运行时验证，不替代 `R2`

详细实验对比、指标定义和收口结论请看：

- `docs/22_real_map_replay_and_optimization.md`
- `docs/23_stage_summary.md`
- `docs/24_next_stage_plan.md`

## 当前推荐参数

以下参数只适用于当前阶段 4、当前这条“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”：

- `tile_width=96`
- `tile_height=96`
- `resolution=0.333333`
- `publish_every_n=1`
- `min_points_per_cell=1`
- `log_every_n=1`

## 暂未进入范围

当前不要把仓库状态理解为已经进入这些阶段：

- 真实双机联调
- Discovery Server 正式实验
- Chrony 时钟同步正式实验
- FAST-LIO2 正式链路
- Nav2 正式链路
- 机械臂正式链路
- 全局融合地图

这些方向仍然是后续阶段候选入口，不是当前仓库已经完成的交付。

## Workspace 结构

```text
air_ground_ws/
├── src/
│   ├── ag_interfaces
│   ├── ag_mock_nodes
│   ├── ag_monitor
│   ├── ag_tf_tools
│   ├── ag_bringup
│   ├── ag_network_tools
│   └── ag_system_tests
├── config/
├── docs/
└── scripts/
```

## 1. Build

```bash
cd /path/to/air_ground_ws
./scripts/build_ws.sh
```

如果你更习惯手动执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

## 2. Source

推荐：

```bash
source scripts/source_ws.sh
```

这个脚本会同时 source：

- `/opt/ros/jazzy/setup.bash`
- `install/setup.bash`

注意：`scripts/source_ws.sh` 必须用 `source` 调用，不能直接执行。

## 3. 单机启动

```bash
./scripts/run_single_machine.sh
```

或者：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch ag_bringup single_machine_mock.launch.py
```

启动后应能看到这些关键 topic：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/tf`
- `/system/delay_probe`

## 4. 双机 / Discovery Server 参考（当前阶段不进入）

下面这些内容保留为后续阶段参考，不代表当前阶段已经进入真实双机联调。

如果后续要切到双机 Discovery Server，可参考 Fast DDS 相关设置：

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
```

双机联调前还要确认：

- 两边 `ROS_DOMAIN_ID` 一致
- 两边不要设置 `ROS_LOCALHOST_ONLY=1`
- 两边都已经 source ROS 2 Jazzy 和本 workspace

### UGV / Server 侧

```bash
./scripts/run_server_discovery.sh <server_ip> 11811
```

### UAV / Client 侧

```bash
./scripts/run_client_discovery.sh <server_ip> 11811
```

如果你想手动启动 Discovery Server，请看：

- `config/fastdds/README_fastdds.md`
- `docs/06_fastdds_discovery_server.md`

## 5. QoS 配置映射

本项目保留了两份 QoS YAML：

- `config/qos/qos_profiles.yaml`
  - 根目录可编辑版本，便于人工查看和修改
- `src/ag_bringup/config/qos_profiles.yaml`
  - 随 `ag_bringup` 安装的运行时版本，launch 和 `qos_inspector` 默认读这份

修改 QoS 时，请同步更新这两份文件。

当前关键映射如下：

- `/uav/map/tile`: Reliable + Transient Local
- `/uav/targets/current`: Reliable + Transient Local
- `/uav/odom`: Best Effort + Volatile
- `/tf`: Best Effort + Volatile
- `/tf_static`: Reliable + Transient Local
- `/system/delay_probe`: Reliable + Volatile

代码侧统一通过 `ag_network_tools/qos_profiles.py` 生成 QoS，避免每个节点自己散写策略。

## 6. 如何验证 topic / tf / delay / bw / hz

```bash
./scripts/check_topics.sh
./scripts/check_hz.sh /uav/odom
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
./scripts/check_tf.sh
```

说明：

- `check_delay.sh` 优先调用 `ros2 topic delay`
- 如果当前环境没有 `ros2 topic delay`，脚本会回退到自定义 `delay_probe_sub`

## 7. rosbag 录制与回放

录制：

```bash
./scripts/record_rosbag.sh bags/mock_run
```

回放：

```bash
./scripts/replay_rosbag.sh bags/mock_run
```

也可以使用回放测试 launch：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py
```

或自动播放：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py auto_play:=true bag_path:=bags/mock_run
```

## 8. 如何替换 mock 节点为真实模块（当前只保留替换点）

建议按下面的映射替换：

- `uav_mock_odom_tf_pub`
  - 替换为 FAST-LIO2 adapter
- `uav_mock_map_tile_pub`
  - 替换为 2.5D map builder adapter
- `uav_mock_target_pub`
  - 替换为 target detector adapter
- `ugv_nav_sink_stub`
  - 替换为 Nav2 adapter
- `frame_alignment_stub`
  - 替换为 EKF / localization alignment adapter
- `arm_target_sink_stub`
  - 替换为 arm target adapter
- `static_tf_loader`
  - 替换为真实外参加载或 hardware bridge

当前代码只保留接口契约和占位，不伪造真实串口、CAN、USB、雷达或机械臂驱动参数。

如果你想先把未来真实模块的占位节点单独跑起来，可以执行：

```bash
ros2 launch ag_bringup future_adapters_stub.launch.py
```

## 9. Chrony 与弱网测试（当前阶段不进入）

Chrony 示例配置：

- `config/chrony/chrony_server.conf`
- `config/chrony/chrony_client.conf`
- `config/chrony/README_chrony.md`
- `scripts/check_chrony.sh`

弱网与 Wi-Fi 测试脚本：

- `scripts/iperf_udp_server.sh`
- `scripts/iperf_udp_client.sh`
- `scripts/apply_netem.sh`
- `scripts/clear_netem.sh`

注意：`apply_netem.sh` 和 `clear_netem.sh` 需要 `sudo`。

## 10. 进一步阅读

- `docs/01_quick_start.md`
- `docs/02_architecture.md`
- `docs/03_debug_playbook.md`
- `docs/04_interface_contracts.md`
- `docs/05_qos_strategy.md`
- `docs/06_fastdds_discovery_server.md`
- `docs/07_chrony_setup.md`
- `docs/08_wifi6_weak_network_test.md`
- `docs/09_rosbag_workflow.md`
- `docs/10_migration_to_jetson.md`
- `docs/11_future_integration_points.md`
- `docs/12_dual_machine_wired_test.md`
- `docs/22_real_map_replay_and_optimization.md`
- `docs/23_stage_summary.md`
- `docs/24_next_stage_plan.md`
- `docs/acceptance_stage1.md`
- `docs/acceptance_stage2_template.md`
- `docs/acceptance_stage3_template.md`
