# 14 Stage2 Rosbag Workflow

## 目标

这份文档描述 stage2 的 rosbag 录制、回放和验收建议，重点对应这两个脚本：

- `./scripts/rosbag_record_stage2.sh`
- `./scripts/rosbag_play_stage2.sh`

适用场景：

- 把一次双机冒烟的 topic 现场固化下来
- 离线复现 stage2 关键 topic 行为
- 在不依赖真实前端在线运行的情况下，继续验证下游订阅、带宽、频率和 delay 观测链路

## 当前会录制哪些 topics

`./scripts/rosbag_record_stage2.sh` 默认录制：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/system/delay_probe`
- `/tf`
- `/tf_static`

这些 topic 覆盖了 stage2 需要看的主要链路：状态、地图块、目标、TF 和时延探针。

## 录制前建议

在开始录制之前，先确认 live 图已经正常：

```bash
./scripts/validate_dual_machine_topics.sh
```

如果这是双机现场，建议同时补记下面这些信息到验收记录里：

- 测试日期和时间
- 机器 A / 机器 B 的 hostname 和 IP
- `ROS_DOMAIN_ID`
- `RMW_IMPLEMENTATION`
- 是否使用 Discovery Server
- bag 输出目录

## 录制流程

在能看到完整 stage2 topics 的那一侧执行：

```bash
./scripts/rosbag_record_stage2.sh bags/stage2_run_01
```

如果不传目录，默认输出到：

```bash
bags/stage2_smoke
```

录制时脚本会打印目标目录，并一直阻塞到你按 `Ctrl+C`。

推荐命名方式：

- `bags/stage2_YYYYMMDD_run01`
- `bags/stage2_default_discovery_run01`
- `bags/stage2_discovery_server_run01`

这样后续更容易区分是默认发现链路还是 Discovery Server 链路。

## 回放流程

最简单的回放方式：

```bash
./scripts/rosbag_play_stage2.sh bags/stage2_run_01
```

这个脚本会自动带上 `--clock`，并提示可以并行执行的检查命令：

- `./scripts/check_hz.sh /uav/odom`
- `./scripts/check_bw.sh /uav/map/tile`
- `./scripts/check_delay.sh /system/delay_probe`
- `ros2 topic echo /uav/targets/current --once`

如果你想先把回放接收端和监控链路准备好，也可以沿用已有回放测试 launch：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py
```

然后在另一个终端执行：

```bash
./scripts/rosbag_play_stage2.sh bags/stage2_run_01
```

## 回放期间的建议验证

回放开始后，推荐至少执行一次：

```bash
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

如果你只想做轻量检查，也可以拆开执行：

```bash
./scripts/validate_dual_machine_topics.sh
./scripts/check_hz.sh /uav/odom
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
ros2 topic echo /uav/targets/current --once
```

## 推荐的两种使用方式

### 1. 真实双机链路录制，离线复盘

顺序建议：

1. 先完成默认发现或 Discovery Server 冒烟
2. 在 live 图稳定后开始录制
3. 停止录制并保存 bag 路径
4. 在同机或另一台开发机上做离线回放
5. 对比 live 现象和回放现象是否一致

### 2. 把 rosbag 当成 stage2 回归输入

顺序建议：

1. 保留一份已知正常的 stage2 bag
2. 每次修改下游节点或 QoS 配置后，重新回放
3. 使用 `stage2_acceptance_check.sh` 观察 topic list、hz、bw、delay 是否明显退化

## 建议保留哪些证据

建议把下面这些内容和 bag 一起留档：

- bag 路径
- 测试时的命令行
- `stage2_acceptance_check.sh` 输出摘要
- 关键 topic 的 `hz` / `bw` / `delay` 观测结果
- 本次测试是 live 双机，还是离线回放

## rosbag 能验证什么

rosbag 回放适合验证：

- 下游节点能否正确订阅 stage2 topics
- 关键 topic 是否仍然存在
- 频率、带宽、delay 观测链路是否还能工作
- 回放环境下的 TF 和目标消息是否可见

## rosbag 不能替代什么

仅靠 rosbag 回放，不能声称下面这些内容已经被验证：

- 真实双机网络互通
- 默认发现跨机稳定性
- Discovery Server 真实运行状态
- 实际跨机带宽、丢包和时延
- 长时间在线运行的发现恢复能力

所以如果本次只做了录包或回放，没有真实双机现场，就需要在验收记录里明确写成“离线验证通过，双机现场待补测”。
