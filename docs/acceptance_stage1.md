# Acceptance Stage 1

## 测试目的

确认当前 `air_ground_ws` 的单机 loopback mock 通信闭环已经可用，并作为后续双机和真实模块替换的基线。

## 测试环境

- Ubuntu 24.04
- ROS 2 Jazzy
- 单机 workspace：`air_ground_ws`
- 模式：`single_machine_mock.launch.py`

## 执行命令

```bash
./scripts/build_ws.sh
source scripts/source_ws.sh
ros2 launch ag_bringup single_machine_mock.launch.py
./scripts/check_topics.sh
./scripts/check_hz.sh /uav/odom
ros2 topic echo /uav/targets/current --once
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
./scripts/check_tf.sh
```

## 预期现象

- workspace 能成功 build
- 单机 launch 能启动
- 能看到关键 topics：
  - `/uav/odom`
  - `/uav/map/tile`
  - `/uav/targets/current`
  - `/system/delay_probe`
  - `/tf`
- `/uav/odom` 频率正常
- `/uav/targets/current` 可以被 echo
- `/uav/map/tile` 可以被 `ros2 topic bw` 统计

## 实际结果

- 已确认 `colcon build --symlink-install` 可通过
- 已确认单机 loopback mock 通信可运行
- 已确认关键 topics 存在并可观测：
  - `/uav/odom`
  - `/uav/map/tile`
  - `/uav/targets/current`
  - `/system/delay_probe`
  - `/tf`
- 已确认 `/uav/odom` 频率正常
- 已确认 `/uav/targets/current` 可被 `echo`
- 已确认 `/uav/map/tile` 可被 `bw` 统计

## 失败排查点

- 是否已 source `/opt/ros/jazzy/setup.bash`
- 是否已 source `install/setup.bash`
- 是否在 workspace 根目录执行
- `single_machine_mock.launch.py` 是否被误改
- 自定义消息和 Python 包是否重新 build

## 是否通过

- 是
