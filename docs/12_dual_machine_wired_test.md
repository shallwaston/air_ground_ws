# 12 Dual Machine Wired Test

## 目标

这个文档用于准备两台机器的有线联调，先完成最基础的“能互通、能发现、能看到 topic”，再切换到 Discovery Server。

推荐顺序：

1. 双机网络联通
2. `ping` 验证
3. `iperf3` TCP / UDP 基线
4. 双机默认发现
5. 双机 Discovery Server

## 两台机器各自要准备什么

两边都建议准备：

- Ubuntu 24.04
- ROS 2 Jazzy
- 同一份 `air_ground_ws`
- 已执行 `colcon build --symlink-install`
- 已知本机 IP
- 同一网段的有线连接

UGV / server 端额外建议准备：

- `fastdds` CLI
- Chrony server 配置

UAV / client 端额外建议准备：

- Chrony client 配置

## 先确认两台机器能 ping 通

在 UGV 端：

```bash
ping <uav_ip>
```

在 UAV 端：

```bash
ping <ugv_ip>
```

如果 ping 不通，先不要排查 ROS 2，优先排查：

- 网线/交换机
- IP 配置
- 防火墙
- 网段是否一致

## 用 iperf3 做 TCP / UDP 基线测试

### TCP 基线

在 UGV 端：

```bash
iperf3 -s
```

在 UAV 端：

```bash
iperf3 -c <ugv_ip>
```

### UDP 基线

在 UGV 端：

```bash
./scripts/iperf_udp_server.sh
```

在 UAV 端：

```bash
./scripts/iperf_udp_client.sh <ugv_ip> 50M 30 5201
```

如果 `iperf3` 不存在，先安装它，再进入 ROS 双机联调。

## 双机 ROS 环境的硬性要求

### 1. 不能使用 `ROS_LOCALHOST_ONLY=1`

双机测试前请检查：

```bash
echo "${ROS_LOCALHOST_ONLY:-unset}"
```

如果值是 `1`，请执行：

```bash
unset ROS_LOCALHOST_ONLY
```

### 2. 两边 `ROS_DOMAIN_ID` 必须一致

例如两边都用：

```bash
export ROS_DOMAIN_ID=0
```

不要求必须是 `0`，但必须一致。

### 3. 推荐两边使用同一个 RMW

建议两边都设置：

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

这样在切到 Discovery Server 时不会引入额外变量。

## 两边如何 source 环境

UGV 端：

```bash
cd /path/to/air_ground_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

UAV 端：

```bash
cd /path/to/air_ground_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

也可以直接执行：

```bash
source scripts/source_ws.sh
```

## 先不用 Discovery Server 的基础双机可见性验证

这一步的目的是先确认“默认发现”就已经通了。

### UGV / server 端

```bash
cd /path/to/air_ground_ws
source scripts/source_ws.sh
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_server.launch.py
```

### UAV / client 端

```bash
cd /path/to/air_ground_ws
source scripts/source_ws.sh
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_client.launch.py
```

### 如何确认已经互相看见

建议在 UGV 端检查：

```bash
./scripts/check_topics.sh
```

重点看是否能看到：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`

如果默认发现都不通，不要先切 Discovery Server，先把基础网络和环境变量问题排干净。

## 如何切换到 Discovery Server 模式

### 第一步：UGV 端确认 CLI

```bash
which fastdds
```

### 第二步：UGV 端启动 server 侧

推荐：

```bash
./scripts/run_server_discovery.sh <ugv_ip> 11811
```

等价手动方式：

终端 A：

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<ugv_ip>:11811
fastdds discovery -i 0 -l 11811
```

终端 B：

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<ugv_ip>:11811
ros2 launch ag_bringup dual_machine_server.launch.py
```

### 第三步：UAV 端启动 client 侧

推荐：

```bash
./scripts/run_client_discovery.sh <ugv_ip> 11811
```

等价手动方式：

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<ugv_ip>:11811
ros2 launch ag_bringup dual_machine_client.launch.py
```

## 失败时优先排查什么

按优先级建议这样排：

1. 两台机器是否真的能 ping 通
2. `ROS_LOCALHOST_ONLY` 是否误设成 `1`
3. `ROS_DOMAIN_ID` 是否两边一致
4. 是否已经正确 source 了 ROS 和 workspace
5. `RMW_IMPLEMENTATION` 是否为 `rmw_fastrtps_cpp`
6. `ROS_DISCOVERY_SERVER` 是否写成真实 UGV IP
7. `fastdds` CLI 是否真的存在并成功启动
8. 防火墙是否阻断

## 建议的最小联调流程

1. `ping`
2. `iperf3`
3. 双机默认发现
4. 双机 Discovery Server
5. Chrony 检查
6. 再进入弱网和 rosbag 测试
