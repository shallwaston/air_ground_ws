# 10 Migration To Jetson

## 迁移目标

当前工程优先面向 Ubuntu 24.04 + ROS 2 Jazzy 的通用开发机，但目录结构和依赖设计已经尽量保持 Jetson 迁移友好。

## 建议迁移顺序

1. 先在 x86 单机跑通
2. 再在双机网络上跑通
3. 最后再迁到 Jetson

不要一开始就在 Jetson 上同时排查：

- ROS 环境问题
- 网络问题
- 算法问题
- 驱动问题

## Jetson 上优先保留不变的部分

- `ag_interfaces`
- `ag_network_tools`
- `ag_bringup`
- 大部分 monitor 节点
- 大部分测试脚本

## 迁移时最可能替换的部分

- `uav_mock_odom_tf_pub`
  - 替换为 FAST-LIO2 adapter
- `uav_mock_map_tile_pub`
  - 替换为真实地图构建器
- `uav_mock_target_pub`
  - 替换为真实 detector adapter
- `frame_alignment_stub`
  - 替换为 EKF / localization adapter

## Jetson 上需要重点关注

- CPU 占用
- 内存占用
- DDS 大消息传输
- Wi-Fi 驱动稳定性
- 存储写入性能
- rosbag 写盘能力

## 本项目刻意没有提前写死的内容

- 设备串口号
- CAN 参数
- USB 端口
- 具体雷达型号参数
- 机械臂驱动细节

这些内容必须等 Jetson 真机阶段再定，避免“现在写得很像真相，实际上完全不可用”。
