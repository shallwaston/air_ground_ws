# 06 Fast DDS Discovery Server

## 目标和适用范围

本项目默认推荐用 Fast DDS Discovery Server 拓扑，而不是依赖局域网广播发现。

这样做的原因：

- 双机部署更稳定
- 弱网和复杂网段更容易控制
- 后续扩展到多 UAV / 多 UGV 时更好管理

但在真正切到 Discovery Server 之前，建议先完成两步基线验证：

1. 单机 loopback
2. 双机默认发现

## 推荐环境变量

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
```

说明：

- `<server_ip>` 是示例占位符，必须换成真实 UGV / server IP
- `11811` 是示例端口，可以改，但要保持两端一致
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` 是推荐前提

## 三种运行模式的区别

### 1. 单机 loopback

用途：

- 保持当前 mock 系统自测闭环
- 不需要跨机器发现

典型命令：

```bash
./scripts/run_single_machine.sh
```

### 2. 双机默认发现

用途：

- 先验证两台机器网络和 ROS 2 默认发现没有问题
- 先不引入 Discovery Server 变量

要求：

- 两边 `ROS_DOMAIN_ID` 一致
- 两边不能设置 `ROS_LOCALHOST_ONLY=1`
- 两边同网段、可互相 ping 通
- 两边都 source 了 ROS 和 workspace

这一模式的详细步骤请看：

- `docs/12_dual_machine_wired_test.md`

### 3. 双机 Discovery Server

用途：

- 更稳定地管理双机或多机发现
- 作为后续弱网和多节点扩展的推荐模式

要求：

- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `ROS_DISCOVERY_SERVER=<server_ip>:11811`

## 先检查 Fast DDS CLI 是否存在

在 UGV/server 端先执行：

```bash
which fastdds
```

如果能打印出路径，说明 `fastdds` CLI 已安装，可以直接启动 Discovery Server。

如果没有输出：

- 先安装 Fast DDS CLI 工具
- 或者先保留环境变量和文档说明，暂时只做双机默认发现验证
- 当前的 `run_server_discovery.sh` 会在 CLI 缺失时给出保守提示，但不会编造替代 server 进程

## 启动 Discovery Server

UGV / server 机器上建议单独开一个终端：

```bash
fastdds discovery -i 0 -l 11811
```

如果你的 Fast DDS CLI 版本不同，请在真机上执行：

```bash
fastdds discovery --help
```

## 新手操作清单

1. 在两台机器上确认网络互通和 `ROS_DOMAIN_ID` 一致
2. 在两台机器上确认没有 `ROS_LOCALHOST_ONLY=1`
3. 在 UGV 端执行 `which fastdds`
4. 如果 `fastdds` 存在，在 UGV 端启动 Discovery Server
5. 在 UGV 和 UAV 两边都导出：
   - `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
   - `FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml`
   - `ROS_DISCOVERY_SERVER=<server_ip>:11811`
6. 在 UGV 端启动 `dual_machine_server.launch.py`
7. 在 UAV 端启动 `dual_machine_client.launch.py`
8. 用 `ros2 topic list`、`./scripts/check_topics.sh`、`./scripts/check_delay.sh` 验证链路

## 单机验证

终端 1：

```bash
fastdds discovery -i 0 -l 11811
```

终端 2：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=127.0.0.1:11811
ros2 launch ag_bringup single_machine_mock.launch.py
```

## 双机默认发现验证

这一模式不使用 Discovery Server，只用于先检查基础双机连通性。

UGV 端：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_server.launch.py
```

UAV 端：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_client.launch.py
```

## 双机 Discovery Server 验证

### UGV / Server 侧

推荐脚本：

```bash
./scripts/run_server_discovery.sh <server_ip> 11811
```

等价的手动方式：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
ros2 launch ag_bringup dual_machine_server.launch.py
```

### UAV / Client 侧

推荐脚本：

```bash
./scripts/run_client_discovery.sh <server_ip> 11811
```

等价的手动方式：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
ros2 launch ag_bringup dual_machine_client.launch.py
```

## 推荐脚本入口

更适合新手的方式：

```bash
./scripts/run_server_discovery.sh <server_ip> 11811
./scripts/run_client_discovery.sh <server_ip> 11811
```

如果 `which fastdds` 没有结果，`run_server_discovery.sh` 仍然会启动 server 侧 ROS 节点，但不会伪造 Discovery Server 进程。

## 当前 XML 为什么故意保持极简

`config/fastdds/fastdds_profiles.xml` 只放了一个最小可解释 profile，原因是：

- 真实 transport buffer
- interface whitelist
- discovery redundancy
- Wi-Fi 6 细节

这些都必须在真机网络上调，不能凭空编造。

## 常见问题

### 两端都启动了但互相发现不到

先确认：

- server IP 不是示例值
- 端口一致
- 双方网络互通
- 防火墙未阻断
- `RMW_IMPLEMENTATION` 真的是 `rmw_fastrtps_cpp`
- 两边 `ROS_DOMAIN_ID` 一致
- 没有设置 `ROS_LOCALHOST_ONLY=1`

### 单机正常，双机不正常

优先怀疑：

- 默认发现模式下网段或广播被限制
- `ROS_DISCOVERY_SERVER` 填错
- Discovery Server 没跑起来
- Chrony 未同步导致日志判断混乱
- Wi-Fi 链路弱
