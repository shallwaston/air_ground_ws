# 22. Real Map Replay And Optimization

## 1. 目标和边界

本文档只覆盖当前阶段已经打通的“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”。

当前结论的适用边界如下：

- 输入来自离线公开真实点云样本回放，不是在线传感器直连。
- `/uav/map/tile` 的消息名保持不变。
- `MapTile.msg` 保持不变。
- `single_machine_mock.launch.py` 行为保持不变。
- 当前链路不涉及双机、Discovery Server、Chrony、FAST-LIO2 正式链路、Nav2、机械臂正式链路。
- 当前结果不能表述成全局融合地图。

## 2. 数据源说明与偏差说明

当前实验的数据源是离线 rosbag 中的公开真实点云样本，输入主题为 `/lidar_points`，经 `pointcloud_to_maptile_adapter` 转换后发布到 `/uav/map/tile`。

这类离线 replay 数据有两个需要明确说明的偏差：

- 样本时间戳来自 bag 录制时刻，不代表当前回放机器的实时传感器采集时间。
- 回放路径上的测量结果会受到 bag 播放速率、启动时序、warmup 窗口和本机负载影响。

因此，当前实验更适合回答“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验在本地 replay 场景下是否跑通、频率和负载大致如何、构图耗时是否稳定”，不适合直接回答真实在线系统的全链路端到端时延。

## 3. 地图语义说明

`pointcloud_to_maptile_adapter` 当前输出的是 local / scan-aligned / 非全局融合地图语义：

- 每个 `MapTile` 只由一帧输入点云样本构建。
- tile 对齐输入点云自身坐标系，或对齐 `local_frame_override` 指定的局部参考系。
- 输出是局部 2.5D tile，不做多帧累积融合。
- 不提供全局一致性、回环、全局拼接或长期地图维护语义。

因此 `/uav/map/tile` 在当前阶段应理解为上述“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”中的局部输出，而不是“全局融合地图”。

## 4. 时间戳语义说明

当前链路中需要区分两个时间戳：

- `source_stamp`
  - 透传输入点云 `header.stamp`
  - 语义是原始样本采集时间
- `header.stamp`
  - 由 `pointcloud_to_maptile_adapter` 在发布 `MapTile` 时填写
  - 语义是当前 `MapTile` 发布时间

对应理解如下：

- `source_stamp` 用来保留原始样本时间基。
- `header.stamp` 用来观察 replay 路径中从适配器发布到下游消费的近端链路时序。
- `seq` 由适配器本地维护，要求严格递增，用于观察是否存在跳号或丢包迹象。

## 5. 指标说明

### `topic_hz`

`/uav/map/tile` 在测量窗口内的平均发布频率。

### `topic_bw`

`/uav/map/tile` 在测量窗口内的平均带宽，当前统计口径来自消息序列化字节数的平均值。

### `header_latency_ms`

下游节点用 `now - header.stamp` 得到的时延。它更接近“适配器发布后到下游观察到消息”为止的近端链路延迟。

### `source_latency_ms`

下游节点用 `now - source_stamp` 得到的时延。对于离线 bag replay，它会混入“样本原始采集时间与当前回放墙钟时间不一致”的影响。

在当前实验里，`source_latency_ms` 的局限性非常明显：

- 它不应被解释成真实在线链路的端到端时延。
- 它可以作为“时间基不一致”的告警信号。
- 对离线 bag，出现极大数值是预期内现象。

### `build_ms_mean / build_ms_max / build_ms_p95`

适配器发布 build report 时输出的局部构图耗时统计：

- `build_ms_mean`：滑动窗口平均值
- `build_ms_max`：滑动窗口最大值
- `build_ms_p95`：滑动窗口 95 分位值

这三个值用于观察构图是否稳定，以及参数调整是否带来尾时延恶化。

### `known_ratio`

当前 tile 中已知栅格占比，可作为局部地图覆盖程度的近似指标。

### `known_cell_count`

`known_cell_count ~= known_ratio * tile_width * tile_height`，可作为“当前表达中已知栅格总数”的辅助指标。

使用时需要注意：

- 当 `tile_width`、`tile_height` 或 `resolution` 改变时，`known_cell_count` 会受到空间离散粒度变化影响。
- 它可以作为“表达变粗”的辅助证据。
- 它不能单独作为地图质量恶化的主证据。

### `known_area`

`known_area ~= known_ratio * tile_width * tile_height * resolution^2`，可作为“当前局部 tile 中已知覆盖面积”的近似指标。

使用时需要注意：

- `known_area` 上升通常说明覆盖没有缩水。
- `known_area` 与 `known_ratio` 上升，不等价于地图质量全面更优。
- 当表达更粗时，覆盖面积变大与细节分辨率下降可能同时出现。

### `avg_tile_kb`

`avg_tile_kb ~= topic_bw / topic_hz`，用于区分平均带宽变化究竟更接近“单消息体量变化”还是“发布频率变化”。

### `seq_jump_total`

下游消费端累计观察到的 `seq` 跳号总量。当前值为 0 时，可认为测量窗口内未观察到明显序号跳变。

## 6. 阶段 2 参考结果（辅助对照）

当前固定引用 `artifacts/real_map_replay/stage2_phase2_check/summary.txt` 中的实值：

| 指标 | 当前值 |
| --- | --- |
| `topic_hz` | `3.91` |
| `topic_bw` | `320.29KB/s` |
| `header_latency_ms` | `4.92` |
| `source_latency_ms` | `49277155418.58` |
| `build_ms_mean` | `28.06` |
| `build_ms_max` | `46.73` |
| `build_ms_p95` | `35.51` |
| `known_ratio` | `0.140` |
| `seq_jump_total` | `0` |

补充说明：

- `latency_mode=source_stamp`
- `source_latency_ms` 数值很大，原因是离线 bag 的时间基问题，不应被当成真实链路端到端时延
- `map_tile_build_report` 中当前 `frame=hesai_lidar`
- 阶段 4 完成后，阶段 2 结果继续保留为辅助对照，不再作为唯一主锚点

## 7. 阶段 4 最终优化结论

阶段 4 的主比较锚点为 `R0` 有效复测结果，而不是旧的阶段 2 数值。

阶段 4 各轮实验均使用同一 bag、同一 `12s` benchmark 窗口，并在同一个放开权限的 shell 内串行完成 replay、首帧等待与 benchmark，以降低当前环境下跨进程 DDS 发现不稳定带来的偏差。

### 阶段 4 关键指标对比

| 轮次 | 参数摘要 | `topic_hz` | `topic_bw` | `avg_tile_kb` | `header_latency_ms` | `build_ms_mean` | `build_ms_max` | `build_ms_p95` | `known_ratio` | `known_cell_count` | `known_area` | `seq_jump_total` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `R0` | `128x128 @ 0.25m`, `log_every_n=1` | `6.10` | `495.27KB/s` | `81.19` | `2.01` | `11.62` | `19.06` | `17.81` | `0.158` | `2588.67` | `161.79 m^2` | `0` |
| `R1` | `112x112 @ 0.285714m`, `log_every_n=1` | `4.83` | `301.55KB/s` | `62.43` | `3.14` | `11.74` | `22.37` | `17.67` | `0.177` | `2220.29` | `181.25 m^2` | `0` |
| `R2` | `96x96 @ 0.333333m`, `log_every_n=1` | `6.45` | `294.62KB/s` | `45.68` | `1.60` | `11.20` | `18.09` | `14.54` | `0.202` | `1861.63` | `206.85 m^2` | `0` |
| `R3` | `96x96 @ 0.333333m`, `log_every_n=10` | `6.05` | `276.56KB/s` | `45.71` | `1.40` | `8.48` | `19.40` | `12.85` | `0.200` | `1843.20` | `204.80 m^2` | `0` |

### 各轮一句话定性

- `R0`：阶段 4 主锚点基线，用于替代旧的阶段 2 数值作为后续主比较口径。
- `R1`：可信的压缩 trade-off，但不作为推荐参数集；其带宽下降部分来自单消息体量下降，也部分来自 `topic_hz` 下降，不能视为纯压缩收益。
- `R2`：阶段 4 最有竞争力、也是默认推荐的参数组；其带宽下降主要来自 `avg_tile_kb` 显著下降，而不是靠降频获得，同时 `header_latency_ms` 与 `build_ms_*` 也改善，因此相对 `R0` 可判为更优。
- `R3`：基于 `R2` 将 `log_every_n` 从 `1` 调到 `10` 的次要验证轮；局部运行时指标改善，但 `topic_bw` 的下降主要跟随 `topic_hz` 下降，`avg_tile_kb` 基本不变，整体收益不足以替代 `R2` 成为默认推荐配置。

### 阶段 4 推荐参数

在当前阶段 4、当前这条“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”内，默认推荐保留 `R2` 参数组：

- `tile_width: 96`
- `tile_height: 96`
- `resolution: 0.333333`
- `publish_every_n: 1`
- `min_points_per_cell: 1`
- `log_every_n: 1`

补充说明：

- 当前实验只能表述为“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”，不能表述为全局融合地图。
- `source_latency_ms` 在离线 bag 场景下只保留记录，不参与主排序。
- `known_cell_count` 的下降可作为表达变粗的辅助证据，但不能单独作为质量恶化主证据。
- `known_area` 与 `known_ratio` 上升说明覆盖没有缩水，但不等价于地图质量全面更优。
- `R3` 建议记录，但不作为默认推荐配置。

## 8. 运行命令

### workspace source

```bash
source /home/shallwaston/air_ground_ws/scripts/source_ws.sh
```

### 启动 replay launch

```bash
source /home/shallwaston/air_ground_ws/scripts/source_ws.sh
ros2 launch ag_bringup real_map_replay_experiment.launch.py \
  auto_play:=true \
  bag_path:=/home/shallwaston/air_ground_ws/artifacts/real_map_samples/2024-08-23-11-05-41_0_clipped.mcap \
  playback_rate:=1.0
```

### 跑 benchmark

```bash
source /home/shallwaston/air_ground_ws/scripts/source_ws.sh
./scripts/benchmark_real_map_tile.sh <label> 12
```

如需复现实验阶段 4 的可比口径，建议在同一个放开权限的 shell 中串行完成 replay、首帧等待与 benchmark，避免当前环境中的跨进程 DDS 发现不稳定影响结果。

### 查看 summary

```bash
cat /home/shallwaston/air_ground_ws/artifacts/real_map_replay/<label>/summary.txt
```

### 运行测试

优先使用：

```bash
source /home/shallwaston/air_ground_ws/scripts/source_ws.sh
export ROS_HOME=/tmp/air_ground_ws_stage3_tests
export ROS_LOG_DIR=/tmp/air_ground_ws_stage3_tests/log
mkdir -p "$ROS_LOG_DIR"
python3 -m pytest -q src/ag_system_tests/test
```

如需走 `colcon test` 的最小命令，可使用：

```bash
source /home/shallwaston/air_ground_ws/scripts/source_ws.sh
export ROS_HOME=/tmp/air_ground_ws_stage3_tests
export ROS_LOG_DIR=/tmp/air_ground_ws_stage3_tests/log
mkdir -p "$ROS_LOG_DIR"
colcon test --packages-select ag_system_tests --event-handlers console_direct+
```

## 9. 风险与下一步建议

当前主要风险如下：

- 离线 bag 的时间基会放大 `source_latency_ms`，容易被误读成真实链路端到端时延。
- 当前输出只有局部、scan-aligned 语义，若文档或汇报措辞不严谨，容易被误解为全局融合地图。
- 参数优化若只追求 `topic_hz`，可能会牺牲 `known_ratio`、`known_cell_count` 或 `build_ms_p95`。
- 表达更粗时，`known_ratio`、`known_area` 上升并不自动代表地图质量全面更优。

阶段 4 收口后的建议仍应限制在当前实验边界内：

- 在当前阶段 4、当前这条“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”内，默认推荐参数组为 `R2`。
- `R3` 可作为“基于 `R2` 的次要运行时验证结果”保留记录，但不建议替代 `R2` 成为默认配置。
- 若后续需要继续优化，应视为新的独立阶段重新定义目标和边界，而不是继续在阶段 4 内追加自由调参轮次。

## 10. 后续优化轮次记录模板

建议每一轮都单独落盘到 `artifacts/real_map_replay/<label>/summary.txt`，同时在本文档中追加一行记录。

| 轮次 / 日期 | 参数改动 | 改动原因 | `topic_hz` | `topic_bw` | `avg_tile_kb` | `header_latency_ms` | `build_ms_mean` | `build_ms_max` | `build_ms_p95` | `known_ratio` | `known_cell_count` | `known_area` | `seq_jump_total` | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `R0 / 2026-03-17` | `128x128 @ 0.25m`, `log_every_n=1` | 阶段 4 主锚点基线 | `6.10` | `495.27KB/s` | `81.19` | `2.01` | `11.62` | `19.06` | `17.81` | `0.158` | `2588.67` | `161.79 m^2` | `0` | 主锚点基线 |
| `R1 / 2026-03-17` | `112x112 @ 0.285714m`, `log_every_n=1` | 轻度压缩 trade-off 验证 | `4.83` | `301.55KB/s` | `62.43` | `3.14` | `11.74` | `22.37` | `17.67` | `0.177` | `2220.29` | `181.25 m^2` | `0` | 更差 |
| `R2 / 2026-03-17` | `96x96 @ 0.333333m`, `log_every_n=1` | 更激进压缩是否值得 | `6.45` | `294.62KB/s` | `45.68` | `1.60` | `11.20` | `18.09` | `14.54` | `0.202` | `1861.63` | `206.85 m^2` | `0` | 更好，阶段 4 默认推荐 |
| `R3 / 2026-03-17` | `96x96 @ 0.333333m`, `log_every_n=10` | `R2` 基础上做轻度运行时验证 | `6.05` | `276.56KB/s` | `45.71` | `1.40` | `8.48` | `19.40` | `12.85` | `0.200` | `1843.20` | `204.80 m^2` | `0` | 次要验证，记录保留，不替代 `R2` |
| `R? / YYYY-MM-DD` |  |  |  |  |  |  |  |  |  |  |  |  |  | 更好 / 更差 / 无明显收益 |
