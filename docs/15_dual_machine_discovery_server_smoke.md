# 15 Dual Machine Discovery Server Smoke

## 目标

这份文档用于做 stage2 的双机 Discovery Server 冒烟测试，对应以下脚本：

- `./scripts/run_server_discovery.sh`
- `./scripts/run_client_discovery.sh`

建议只有在 `docs/13_dual_machine_default_discovery_smoke.md` 已经通过之后，再进入这一阶段。这样如果 Discovery Server 模式失败，排查范围会明显更小。

## 角色约定

- 机器 A：UGV / server 侧
- 机器 B：UAV / client 侧
- Discovery Server：通常也放在机器 A

## 前提条件

- 两台机器都已完成 `./scripts/build_ws.sh`
- 两台机器都能互相 `ping`
- 两台机器 `ROS_DOMAIN_ID` 一致
- 两台机器不能设置 `ROS_LOCALHOST_ONLY=1`
- 机器 A 知道自己的真实可达 IP

推荐先做一次环境检查：

```bash
./scripts/prepare_dual_machine_env.sh
```

## Fast DDS CLI 的边界说明

`run_server_discovery.sh` 有两种工作方式：

1. `fastdds` CLI 存在
   这时脚本会尝试本机启动 Discovery Server，再拉起 `dual_machine_server.launch.py`
2. `fastdds` CLI 不存在
   这时脚本只会设置环境变量并启动 server 侧 ROS stack，同时打印 warning

因此：

- 如果机器 A 没有 `fastdds` CLI，就不能声称“Discovery Server 已实测运行”
- 没有 `fastdds` CLI 的情况下，最多只能声称“Discovery Server 相关环境变量和 server/client 启动流程已对齐”

现场建议先执行：

```bash
which fastdds
```

## 推荐执行顺序

### 1. 机器 A 启动 server 侧

把 `<ugv_ip>` 换成机器 A 的真实 IP：

```bash
./scripts/run_server_discovery.sh <ugv_ip> 11811
```

脚本会自动设置：

- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
- `FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml`
- `ROS_DISCOVERY_SERVER=<ugv_ip>:11811`

如果 `START_DISCOVERY_SERVER=1` 且本机存在 `fastdds`，脚本还会尝试在后台启动：

```bash
fastdds discovery -i 0 -l 11811
```

### 2. 机器 B 启动 client 侧

同样把 `<ugv_ip>` 换成机器 A 的真实 IP：

```bash
./scripts/run_client_discovery.sh <ugv_ip> 11811
```

## 已有 Discovery Server 进程时怎么做

如果机器 A 已经在其他终端手动启动了 Discovery Server，可以避免脚本重复拉起：

```bash
START_DISCOVERY_SERVER=0 ./scripts/run_server_discovery.sh <ugv_ip> 11811
```

一种常见的手动分终端方式是：

终端 A：

```bash
fastdds discovery -i 0 -l 11811
```

终端 B：

```bash
START_DISCOVERY_SERVER=0 ./scripts/run_server_discovery.sh <ugv_ip> 11811
```

终端 C：

```bash
./scripts/run_client_discovery.sh <ugv_ip> 11811
```

## 如何验证已经发现成功

推荐在能看到全局图的一侧执行：

```bash
./scripts/validate_dual_machine_topics.sh
```

如果想做短时观测，再执行：

```bash
CHECK_DURATION_SEC=8 ./scripts/stage2_acceptance_check.sh
```

最少应能看到这些 topics：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/system/delay_probe`
- `/tf`

## 失败时优先排查

建议按下面顺序排查：

1. `<ugv_ip>` 是否写成真实可达地址，而不是示例值
2. 两边 `ROS_DOMAIN_ID` 是否一致
3. `ROS_LOCALHOST_ONLY` 是否被设成 `1`
4. 机器 A 上的 `fastdds` 是否真的存在并成功运行
5. 端口是否两边一致，默认示例是 `11811`
6. 防火墙是否阻断了 Discovery Server 或 ROS 2 数据流
7. `FASTRTPS_DEFAULT_PROFILES_FILE` 是否指向当前 workspace 的 XML
8. 默认发现模式是否本来就不通，如果默认发现未通，先回到 `docs/13_dual_machine_default_discovery_smoke.md`

## 通过标准

最小通过标准建议定义为：

- 机器 A / 机器 B 都能启动对应脚本
- `ROS_DISCOVERY_SERVER=<ugv_ip>:11811` 两边一致
- 如果声称已验证 Discovery Server 真正在跑，机器 A 必须能确认 `fastdds` CLI 已启动
- `validate_dual_machine_topics.sh` 返回成功
- `stage2_acceptance_check.sh` 能采到关键 topic 的 list、hz、bw、echo、delay 信息

## 这一步不能替代什么

Discovery Server 冒烟通过，也不等于下面这些内容已经验证完毕：

- 弱网环境下 Discovery Server 的稳定性
- 多客户端并发发现
- 长时间运行后的恢复能力
- 真机传感器替换后的消息规模和 QoS 压力

这些仍然需要在真实双机或更复杂网络环境中继续补测，并记录到 `docs/acceptance_stage2_template.md`。
