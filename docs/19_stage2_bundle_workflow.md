# 19 Stage2 Bundle Workflow

这份文档只讲如何把 machine A、machine B、验收文档和 rosbag 信息汇总成一个 bundle 目录。

## 1. 先准备输入

至少准备：

- machine A artifact 目录
- machine B artifact 目录

可选准备：

- rosbag 路径
- 已填写的验收文档路径

一个典型例子：

```bash
RUN_ROOT="artifacts/stage2_runs/20260315_run01"
MACHINE_A_DIR="${RUN_ROOT}/machine_a"
MACHINE_B_DIR="${RUN_ROOT}/machine_b"
ACCEPTANCE_DOC="docs/acceptance_stage2_20260315.md"
BAG_PATH="bags/stage2_20260315_221500"
```

## 2. 创建 bundle

```bash
./scripts/create_stage2_bundle.sh \
  --machine-a-dir "${MACHINE_A_DIR}" \
  --machine-b-dir "${MACHINE_B_DIR}" \
  --acceptance-doc "${ACCEPTANCE_DOC}" \
  --rosbag-path "${BAG_PATH}"
```

如果你想自己指定输出目录：

```bash
./scripts/create_stage2_bundle.sh \
  --machine-a-dir "${MACHINE_A_DIR}" \
  --machine-b-dir "${MACHINE_B_DIR}" \
  --acceptance-doc "${ACCEPTANCE_DOC}" \
  --rosbag-path "${BAG_PATH}" \
  --bundle-dir artifacts/stage2_bundle/run01_bundle
```

## 3. bundle 里会有什么

默认至少会生成：

- `artifacts/stage2_bundle/<timestamp>/machine_a/`
- `artifacts/stage2_bundle/<timestamp>/machine_b/`
- `artifacts/stage2_bundle/<timestamp>/acceptance/`
- `artifacts/stage2_bundle/<timestamp>/bag_info.txt`
- `artifacts/stage2_bundle/<timestamp>/summary.txt`

## 4. rosbag 默认怎么处理

默认不会拷贝 rosbag 数据本体。

脚本只会在 `bag_info.txt` 里记录：

- 你提供的 rosbag 路径
- 该路径当前是否存在
- `bag_copied=no`

这样做的目的是避免 bundle 因为大 bag 变得很重。

## 5. summary.txt 会写什么

`summary.txt` 至少会写清：

- 创建时间
- bundle 输出目录
- machine A 输入目录
- machine B 输入目录
- acceptance 文档来源
- rosbag 路径来源
- 已提供哪些证据
- 缺失哪些证据

## 6. 创建完之后先检查什么

建议至少检查：

```bash
cat artifacts/stage2_bundle/<timestamp>/summary.txt
cat artifacts/stage2_bundle/<timestamp>/bag_info.txt
ls artifacts/stage2_bundle/<timestamp>/machine_a
ls artifacts/stage2_bundle/<timestamp>/machine_b
ls artifacts/stage2_bundle/<timestamp>/acceptance
```

## 7. bundle 能证明什么

bundle 能帮助你证明：

- 机器 A / 机器 B 的日志和证据已经被集中整理
- rosbag 路径和验收文档路径已经被一起记录
- 后续复盘时不需要再人工拼接多个来源

## 8. bundle 不能代替什么

bundle 本身不能代替：

- 真实双机现场
- 真实网络链路验证
- 真实 Discovery Server 运行结果
- 原始 rosbag 数据本体

所以如果现场没有真实双机测试，bundle 只能说明“工具和证据组织方式已经准备好”，不能说明“真实双机 stage2 已通过”。
