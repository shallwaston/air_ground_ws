# 构建与可复现调用

仅在外层核验固定容器、镜像、完整进程清单、独占锁、剩余资源和用户授权后运行。不得创建替代容器或复用 R1/R4/R6 install。所有编译输出必须进入本候选的新目录。

1. 清除继承的 AMENT/CMAKE/COLCON/PYTHONPATH/LD_LIBRARY_PATH/ROS_PACKAGE_PATH，仅加载 `/opt/ros/jazzy/setup.bash`。
2. 在独立 prerequisite 目录只构建本候选 ag_interfaces，使用 `-DCMAKE_SKIP_RPATH=ON`。这是严格入口实际消息依赖的前置生成，不是旧安装产物。
3. 以镜像内 Python 执行 `scripts/prepare_strict_assets.py --interface-prefix NEW_PREFIX/ag_interfaces`。它核对四个 msg 的许可指纹，编译只读 probe，检查每个原生库无 RPATH/RUNPATH，并生成封装及发布 pin。目标存在则拒绝覆盖；保留旧尝试后另行构建。
4. 执行 `./scripts/build_ws.sh --parallel-workers 2`，检查七包前缀、21个原 console 和新增 `lib/ag_network_tools/ag_strict_isolated`。该脚本用 setuptools scripts 安装，未修改原21个 entry_points。
5. source 本候选 install/local_setup.bash，用 production-contract 中的固定入口调用。未知参数、legacy 名称、任意 probe 均拒绝。

Python 调用顺序：create_session（仅返回真实 READY 的拥有者）→ start → receive/query → request_stop(2或15) → wait（真实状态）→ 保存report → close。创建失败需保留异常及子进程状态；活对象不得直接遗弃。一个 Session 只由其创建监督线程管理，外部 reaper 不支持。

生成资产随 Python 包安装：probe C/SO、固定业务源码包、生成消息源码和六个接口原生对象。受审源码文件、发行包 manifest、编译字节的指纹分层绑定，安装位置不是源码身份。R7已验证仅复制完整 ag_network_tools 包及资产、删除继承 overlay 后的三入口运行，不依赖旧源码目录或测试 probe。build/install 缓存本身不是通用跨平台发行包。

正常 CLI 的计划停止不会安装/替换父 handler。父进程如已有 foreign handler，须由其自身生命周期所有者显式调用 API 停止子进程；不能假定任意父SIGTERM都能转发并优雅回收。本版本不提供通用无限阻塞 callback 的强杀恢复策略。
