# 08 Wi-Fi 6 Weak Network Test

## 目标

这个文档描述如何在真实或仿真的无线链路条件下，对本项目进行：

- 带宽测试
- 丢包测试
- 时延抖动测试
- QoS 和大消息传输观察

## 1. 先测原始链路

服务端：

```bash
./scripts/iperf_udp_server.sh
```

客户端：

```bash
./scripts/iperf_udp_client.sh <server_ip> 50M 30 5201
```

这一步先确认 Wi-Fi 6 链路的基础 UDP 能力。

## 2. 启动 QoS 压测

```bash
ros2 launch ag_bringup qos_stress_test.launch.py
```

然后观察：

```bash
./scripts/check_bw.sh /uav/map/tile
./scripts/check_delay.sh /system/delay_probe
```

## 3. 注入弱网

示例：

```bash
sudo ./scripts/apply_netem.sh wlan0 5% 50ms 10ms
```

含义：

- `5%` 丢包
- `50ms` 基础时延
- `10ms` 抖动

## 4. 观察系统反应

重点看：

- `/uav/map/tile` 是否稳定接收
- `ugv_map_tile_sub` 的日志延迟是否明显升高
- `delay_probe_sub` 的均值和最大值是否变化
- `topic_watchdog` 是否开始报错

## 5. 清理 netem

```bash
sudo ./scripts/clear_netem.sh wlan0
```

## 建议测试矩阵

- 无丢包，无附加时延
- 1% 丢包，20ms 时延
- 5% 丢包，50ms 时延，10ms 抖动
- 10% 丢包，100ms 时延，20ms 抖动

## 注意事项

- `apply_netem.sh` 需要 `sudo`
- 不同网卡名可能不是 `wlan0`
- 真实 Wi-Fi 6 环境还应记录 RSSI、MCS、信道占用等信息
- 这些链路层参数本项目没有伪造，建议实机阶段再纳入
