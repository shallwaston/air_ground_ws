# 09 rosbag Workflow

## 为什么 MVP 阶段就要支持 rosbag

因为 rosbag 能帮助你：

- 固化问题现场
- 重放弱网前后的差异
- 替换真实算法前先验证下游行为

## 录制关键 topic

```bash
./scripts/record_rosbag.sh bags/mock_run
```

默认录制：

- `/system/heartbeat`
- `/system/delay_probe`
- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`

## 回放

```bash
./scripts/replay_rosbag.sh bags/mock_run
```

## 回放测试 launch

如果你想先把接收端和监控端启动起来：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py
```

然后另开终端：

```bash
./scripts/replay_rosbag.sh bags/mock_run
```

也可以让 launch 自动播放：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py auto_play:=true bag_path:=bags/mock_run
```

## 推荐用法

### 用 mock 数据先验证 UGV 侧

1. 单机启动 mock 系统
2. 录制一段 bag
3. 只启动接收端和 monitor
4. 回放 bag

### 用真实前端替换 mock 发布端

等 FAST-LIO2 adapter 或真实地图模块接入后，仍然建议保留 rosbag 流程：

- 录制真实前端输出
- 离线回放验证下游
- 比较弱网前后表现

## 注意

如果你在回放时想严格按时间推进系统，请使用 `--clock`，本项目的 `replay_rosbag.sh` 已默认带上。
