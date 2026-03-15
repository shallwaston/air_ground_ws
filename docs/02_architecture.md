# 02 Architecture

## 设计目标

这套工程不是“假装已经接好真实硬件”，而是先搭一个能 build、能 launch、能压测、能替换模块的通信骨架。

核心思路：

- ROS 2 Jazzy
- Fast DDS 思路
- Discovery Server 拓扑
- Python / `rclpy` 优先
- 真实设备细节一律延后到 adapter 层

## 包职责

### `ag_interfaces`

定义跨模块的消息合同：

- `MapTile.msg`
- `TargetInfo.msg`
- `Heartbeat.msg`
- `DelayProbe.msg`

### `ag_network_tools`

统一放公共通信策略：

- topic 常量
- frame 常量
- QoS helper

### `ag_mock_nodes`

模拟 UAV 发布端和 UGV/机械臂接收端：

- UAV odom + TF
- UAV map tile
- UAV targets
- UGV map receiver
- UGV Nav2 sink stub
- arm target sink stub
- heartbeat

### `ag_monitor`

负责可观测性：

- system monitor
- delay probe pub/sub
- topic watchdog
- QoS inspector

### `ag_tf_tools`

负责 TF 骨架：

- `map -> ugv/odom` 对齐占位
- 静态外参加载
- TF 健康检查

### `ag_bringup`

提供 launch 和安装时配置：

- 单机 mock
- 双机 server/client
- QoS stress test
- rosbag replay test

### `ag_system_tests`

提供最小烟测：

- import 测试
- launch smoke 测试
- 消息字段合同测试

## 数据流

### UAV 侧

- `uav_mock_odom_tf_pub` 发布 `/uav/odom` 和 `/tf`
- `uav_mock_map_tile_pub` 发布 `/uav/map/tile`
- `uav_mock_target_pub` 发布 `/uav/targets/current`
- `delay_probe_pub` 发布 `/system/delay_probe`

### UGV / Server 侧

- `ugv_map_tile_sub` 接收地图并统计延迟
- `ugv_nav_sink_stub` 接收地图和目标
- `arm_target_sink_stub` 接收目标
- `delay_probe_sub` 统计链路时延
- `system_monitor` 汇总系统状态

## TF 骨架

默认关键链路：

- `map -> uav/base_link`
- `map -> ugv/odom`
- `ugv/odom -> ugv/base_link`

这保证后续接入真实定位、地图、底盘、机械臂模块时，不需要从零重做 frame 命名。

## 未来替换点

- FAST-LIO2 adapter
- 2.5D map builder adapter
- EKF adapter
- Nav2 adapter
- target detector adapter
- arm target adapter
- hardware bridge

这些点目前只保留 topic / message / frame / launch 接口，不提前猜真实驱动参数。
