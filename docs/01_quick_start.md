# 01 Quick Start

## 目标

在单机上快速验证这套 MVP 工程骨架已经打通：

- build 正常
- launch 正常
- mock topic 正常
- TF 正常
- 延迟探针正常

## 前置条件

- Ubuntu 24.04
- ROS 2 Jazzy
- `colcon`
- 推荐安装 `fastdds` CLI
- 推荐安装 `iperf3`

## 第一步：构建

```bash
cd /path/to/air_ground_ws
./scripts/build_ws.sh
```

## 第二步：加载环境

```bash
source scripts/source_ws.sh
```

## 第三步：启动单机 mock 系统

```bash
./scripts/run_single_machine.sh
```

## 第四步：验证关键 topic

```bash
./scripts/check_topics.sh
```

期望至少看到：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/system/heartbeat`
- `/system/delay_probe`

## 第五步：验证频率、带宽、延迟、TF

```bash
./scripts/check_hz.sh /uav/odom
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
./scripts/check_tf.sh
```

## 第六步：做一次 rosbag 录制

```bash
./scripts/record_rosbag.sh bags/mock_run
```

另开一个终端回放：

```bash
./scripts/replay_rosbag.sh bags/mock_run
```

## 如果你要切到双机

先看：

- `docs/06_fastdds_discovery_server.md`
- `config/fastdds/README_fastdds.md`

建议先单机跑通，再切双机。
