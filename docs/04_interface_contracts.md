# 04 Interface Contracts

## 关键 topics

- `/uav/odom`
  - `nav_msgs/msg/Odometry`
- `/uav/map/tile`
  - `ag_interfaces/msg/MapTile`
- `/uav/targets/current`
  - `ag_interfaces/msg/TargetInfo`
- `/system/heartbeat`
  - `ag_interfaces/msg/Heartbeat`
- `/system/delay_probe`
  - `ag_interfaces/msg/DelayProbe`

## `MapTile.msg`

用途：

- UAV 向 UGV 下发 2.5D 地图切片
- 后续做 QoS / 带宽 / 延迟统计

关键字段：

- `header`
- `resolution`
- `width`
- `height`
- `origin`
- `elevation`
- `traversability`
- `source_stamp`
- `seq`

约束建议：

- `elevation` 与 `traversability` 长度应与地图栅格规模一致
- `source_stamp` 必须由发布端填写
- `seq` 用于统计丢包、乱序和接收进度

## `TargetInfo.msg`

用途：

- 目标检测结果的最小合同
- 后续接 perception / arm / task planner

关键字段：

- `target_id`
- `pose`
- `confidence`

## `Heartbeat.msg`

用途：

- 统一的系统存活上报
- 给 `system_monitor` 做聚合

建议状态值：

- `0`: unknown
- `1`: ok
- `2`: warn
- `3`: error

## `DelayProbe.msg`

用途：

- 端到端延迟测量
- 新环境无法直接使用 `ros2 topic delay` 时的回退方案

关键字段：

- `seq`
- `source_stamp`
- `payload_bytes`

说明：

- `payload_bytes` 目前是元数据字段，用来标记测试规模
- 真正的大消息压力测试建议仍以 `MapTile` 为主

## 未来 adapter 约束

### FAST-LIO2 adapter

- 输出仍需对齐到 `/uav/odom`
- TF 中至少需要保留 `uav/base_link`

### 2.5D map builder adapter

- 输出仍需对齐到 `/uav/map/tile`
- 必须继续填写 `source_stamp` 和 `seq`

### Nav2 adapter

- 先替换 `ugv_nav_sink_stub`
- 不改上游 topic 合同

### EKF adapter

- 先替换 `frame_alignment_stub`
- 保持 `map -> ugv/odom` 这条逻辑接口不变

### arm target adapter

- 先替换 `arm_target_sink_stub`
- 继续消费 `TargetInfo`

### hardware bridge

- 作为设备层桥接入口
- 串口、CAN、USB 参数必须等真机阶段再定
