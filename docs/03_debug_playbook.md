# 03 Debug Playbook

## 1. build 失败

先检查：

- `source /opt/ros/jazzy/setup.bash` 是否执行
- `colcon` 是否安装
- 是否在 workspace 根目录

推荐先跑：

```bash
./scripts/build_ws.sh
```

## 2. launch 能起但没有 topic

先确认环境已 source：

```bash
source scripts/source_ws.sh
./scripts/check_topics.sh
```

如果还是没有：

- 看 launch 终端是否有 import error
- 看 `package.xml` 和 `setup.py` 是否被正确安装
- 看 `colcon build --symlink-install` 是否最新执行过

## 3. 有 topic 但没有数据

重点检查：

- `/uav/map/tile`
- `/uav/odom`
- `/uav/targets/current`
- `/system/delay_probe`

工具：

```bash
./scripts/check_hz.sh /uav/odom
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
```

## 4. TF 不完整

跑：

```bash
./scripts/check_tf.sh
```

重点看这几个关系：

- `map <- uav/base_link`
- `map <- ugv/odom`
- `ugv/odom <- ugv/base_link`

如果缺失：

- 看 `uav_mock_odom_tf_pub` 是否启动
- 看 `frame_alignment_stub` 是否启动
- 看 `static_tf_loader` 是否成功读取 yaml

## 5. 双机模式看不到对端

先检查环境变量：

```bash
echo $RMW_IMPLEMENTATION
echo $ROS_DISCOVERY_SERVER
echo $FASTRTPS_DEFAULT_PROFILES_FILE
```

应该满足：

- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `ROS_DISCOVERY_SERVER=<server_ip>:11811`

再检查：

- Discovery Server 是否真的启动
- UAV 与 UGV 是否能互 ping
- 防火墙是否放行
- server IP 是否写成了例子值

## 6. 延迟很高

先区分是单机还是双机。

单机高延迟通常说明：

- 机器负载高
- 消息尺寸过大
- launch 太多节点同时打印日志

双机高延迟通常还要检查：

- Chrony 是否同步
- Wi-Fi 是否弱网
- QoS 是否选错
- Discovery Server 所在机器是否过载

## 7. 弱网测试后忘记恢复

如果你执行过 `apply_netem.sh`，记得清理：

```bash
sudo ./scripts/clear_netem.sh wlan0
```

## 8. rosbag 回放无效

先确认：

- bag 路径正确
- sink 节点已启动
- 回放 topic 名和当前系统 topic 名一致

建议先跑：

```bash
ros2 launch ag_bringup rosbag_replay_test.launch.py
./scripts/replay_rosbag.sh bags/mock_run
```
