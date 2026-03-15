# 21 Stage2 Bundle Validation

这份文档只讲如何在 bundle 创建后做一次只读校验。

## 1. 最简单的用法

```bash
./scripts/validate_stage2_bundle.sh \
  --bundle-dir artifacts/stage2_bundle/run01_bundle
```

或者如果 bundle 放在某一轮 run 目录里：

```bash
./scripts/validate_stage2_bundle.sh \
  --bundle-dir artifacts/stage2_runs/20260315_run01/bundle/final_bundle
```

## 2. 这个脚本会检查什么

至少会检查：

- `machine_a/` 是否存在
- `machine_b/` 是否存在
- `acceptance/` 是否存在
- `summary.txt` 是否存在
- `bag_info.txt` 或 `bag_path.txt` 是否存在

还会尽量继续检查：

- `machine_a/` 下是否有 `command.txt` 或日志文件
- `machine_b/` 下是否有 `command.txt` 或日志文件
- `acceptance/` 下是否至少有一个验收输出或文档
- `summary.txt` 是否记录了 machine A / machine B 来源
- `bag_info.txt` 是否提示 rosbag 路径缺失

## 3. PASS / WARN / FAIL 分别代表什么

- `PASS`
  bundle 结构基本完整，主要证据都在
- `WARN`
  bundle 根目录有效，但有缺项、占位项或信息不足
- `FAIL`
  bundle 根目录有效，但关键结构缺失，比如 `machine_a/`、`machine_b/`、`summary.txt` 这类核心内容不完整

退出码规则：

- `0`
  PASS
- `1`
  WARN 或 FAIL
- `2`
  参数错误，或者给定的 bundle 根目录本身无效

## 4. 推荐的实际顺序

先创建 bundle：

```bash
./scripts/create_stage2_bundle.sh \
  --machine-a-dir artifacts/stage2_runs/20260315_run01/machine_a \
  --machine-b-dir artifacts/stage2_runs/20260315_run01/machine_b \
  --acceptance-doc docs/acceptance_stage2_20260315.md \
  --rosbag-path bags/stage2_20260315_221500 \
  --bundle-dir artifacts/stage2_runs/20260315_run01/bundle/final_bundle
```

再做校验：

```bash
./scripts/validate_stage2_bundle.sh \
  --bundle-dir artifacts/stage2_runs/20260315_run01/bundle/final_bundle
```

## 5. 如果出现 WARN 先看哪里

优先看：

1. `summary.txt`
2. `bag_info.txt`
3. `machine_a/`
4. `machine_b/`
5. `acceptance/`

通常 WARN 的含义是：

- 路径记录缺了
- 验收文档没放进去
- rosbag 只记录了路径但没提供
- 某一侧目录有证据，但还不够完整

## 6. bundle 校验通过能证明什么

bundle 校验通过能帮助你证明：

- 证据目录结构是完整的
- machine A / machine B / acceptance / bag 信息已经被整理到一起

## 7. bundle 校验通过不能证明什么

bundle 校验通过不等于：

- 真实双机通信已经验证
- 默认发现一定成功
- Discovery Server 一定成功
- 真实网络质量一定满足要求

它只能说明：

- 证据组织层面基本齐了

真正的双机结论仍然要看现场日志、证据采集结果、rosbag 和验收文档内容。
