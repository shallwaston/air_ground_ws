# 23 Stage Summary

## 本阶段目标

本阶段的目标不是直接进入真实双机和重型系统集成，而是先把基于 ROS 2 分布式架构的异构空地协同建图与精准抓取系统的通信框架、工程骨架、调试/验收工具链和最小可验证链路搭起来。

当前阶段的重点是：

- 单机 mock 基线跑通
- 工程骨架和接口契约稳定
- 真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验打通
- benchmark、summary、QoS、测试、文档收口

## 已完成内容

### 1. 单机基线已通过

`single_machine_mock.launch.py` 可运行，且以下 topic / TF 已验证：

- `/uav/odom`
- `/uav/map/tile`
- `/uav/targets/current`
- `/system/delay_probe`
- `/tf`
- `/tf_static`

### 2. 工程骨架已搭好

当前 workspace 已形成以下包结构：

- `ag_interfaces`
- `ag_mock_nodes`
- `ag_monitor`
- `ag_tf_tools`
- `ag_bringup`
- `ag_network_tools`
- `ag_system_tests`

### 3. 阶段 1 到阶段 3 已完成

- `/lidar_points -> pointcloud_to_maptile_adapter -> /uav/map/tile` 已打通
- `real_map_replay_experiment.launch.py` 可运行
- 真实公开点云样本已能驱动 `/uav/map/tile` 发布
- benchmark / summary / QoS / 测试 / 文档已收口

## 关键实验与验证链路

当前最关键的已验证链路是：

`/lidar_points -> pointcloud_to_maptile_adapter -> /uav/map/tile`

该链路的实验口径必须严格限定为：

`真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验`

它不能上升表述为全局融合地图。

## 阶段 4 收口结论

阶段 4 的主比较锚点为 `R0` 有效复测结果，阶段 2 结果继续保留为辅助对照，不再作为唯一主锚点。

### `R0`

- 主锚点基线
- 用于替代旧的阶段 2 数值作为阶段 4 主比较口径

### `R1`

- 可信的压缩 trade-off 结果
- 不作为推荐参数集
- 带宽下降部分来自单消息体量下降，也部分来自 `topic_hz` 下降，不能视为纯压缩收益

### `R2`

- 阶段 4 最有竞争力、也是默认推荐的参数组
- 带宽下降主要来自 `avg_tile_kb` 显著下降，而不是靠降频获得
- `header_latency_ms` 与 `build_ms_*` 同步改善，因此相对 `R0` 可判为更优

### `R3`

- 基于 `R2` 将 `log_every_n` 从 `1` 调到 `10` 的次要运行时验证轮
- 局部运行时指标有所改善
- 但 `topic_bw` 的下降主要跟随 `topic_hz` 下降，`avg_tile_kb` 基本不变
- 整体收益不足以替代 `R2` 成为默认推荐配置

详细指标对比请看：

- `docs/22_real_map_replay_and_optimization.md`

## 当前推荐配置与适用范围

在当前阶段 4、当前这条“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”内，默认推荐保留 `R2` 参数组：

- `tile_width=96`
- `tile_height=96`
- `resolution=0.333333`
- `publish_every_n=1`
- `min_points_per_cell=1`
- `log_every_n=1`

适用范围说明：

- 该推荐只适用于当前单机 replay + adapter + benchmark 链路
- 不应外推成整个项目的永久默认参数
- 不应外推成未来 FAST-LIO2、Nav2、机械臂或真实双机阶段的默认参数

## 当前边界与限制

当前阶段明确不进入以下范围：

- 真实双机联调
- Discovery Server 正式实验
- Chrony 时钟同步正式实验
- FAST-LIO2 正式链路
- Nav2 正式链路
- 机械臂正式链路
- 全局融合地图

## 当前遗留风险

- 离线 bag 的时间基会放大 `source_latency_ms`，因此它只保留记录，不参与主排序
- 当前实验仍然只是局部、scan-aligned 2.5D MapTile 链路实验，若汇报措辞不严谨，容易被误解为全局融合地图
- `known_cell_count` 的下降可作为表达变粗的辅助证据，但不能单独作为质量恶化主证据
- `known_area` / `known_ratio` 上升说明已知覆盖没有缩水，但不等价于地图质量全面更优

## 阶段性成果一句话总结

当前 workspace 已完成单机通信骨架、mock 基线、“真实点云样本驱动的局部、scan-aligned 2.5D MapTile 链路实验”、配套 benchmark / 测试 / 文档收口，并在阶段 4 内把 `R2` 收敛为当前实验链路默认推荐参数组。
