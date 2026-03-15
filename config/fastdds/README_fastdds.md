# Fast DDS Discovery Server Notes

This folder contains a minimal Fast DDS profile example for the `air_ground_ws` MVP.

## First decide which mode you are testing

### 1. Single-machine loopback

Use this when you only want to confirm the local mock stack still works:

```bash
./scripts/run_single_machine.sh
```

### 2. Dual-machine default discovery

Use this when you want to verify two wired machines can already see each other before introducing Discovery Server.

In this mode:

- do not set `ROS_DISCOVERY_SERVER`
- do not set `ROS_LOCALHOST_ONLY=1`
- keep `ROS_DOMAIN_ID` the same on both machines

### 3. Dual-machine Discovery Server

Use this when the two-machine baseline already works and you want the recommended Fast DDS topology.

## Check whether the Fast DDS CLI exists

```bash
which fastdds
```

If `which fastdds` prints a path, you can start the Discovery Server directly.

If it prints nothing:

- install the Fast DDS CLI tool on the UGV/server machine
- or keep only the environment-variable guidance for now and validate dual-machine default discovery first

## Recommended environment variables

```bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
```

`<server_ip>` is an example placeholder. Replace it with the real UGV/server IP on your test network.

## Start the Discovery Server

On the UGV/server machine, in a dedicated terminal:

```bash
fastdds discovery -i 0 -l 11811
```

If your Fast DDS CLI uses a different version or option format, check `fastdds discovery --help` on the target machine. The command above is the common minimal pattern for Jazzy-era setups.

## Single-machine validation with Discovery Server

In terminal 1:

```bash
fastdds discovery -i 0 -l 11811
```

In terminal 2:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=127.0.0.1:11811
ros2 launch ag_bringup single_machine_mock.launch.py
```

## Dual-machine default discovery validation

On the UGV/server machine:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_server.launch.py
```

On the UAV/client machine:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=0
ros2 launch ag_bringup dual_machine_client.launch.py
```

## Dual-machine Discovery Server validation

On the UGV/server machine:

Recommended:

```bash
./scripts/run_server_discovery.sh <server_ip> 11811
```

Manual:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
ros2 launch ag_bringup dual_machine_server.launch.py
```

On the UAV/client machine:

Recommended:

```bash
./scripts/run_client_discovery.sh <server_ip> 11811
```

Manual:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/config/fastdds/fastdds_profiles.xml
export ROS_DISCOVERY_SERVER=<server_ip>:11811
ros2 launch ag_bringup dual_machine_client.launch.py
```

## Minimal new-user checklist

1. Confirm the two machines can ping each other
2. Confirm the same `ROS_DOMAIN_ID` is set on both machines
3. Confirm `ROS_LOCALHOST_ONLY` is unset or `0`
4. Run `which fastdds` on the UGV/server machine
5. Start the Discovery Server on the UGV machine
6. Run the server-side ROS launch on the UGV machine
7. Run the client-side ROS launch on the UAV machine
8. Check topics, delay, and TF with the scripts in `scripts/`

## What is intentionally left as a TODO

- Transport buffer sizes
- Interface whitelists
- Discovery server redundancy
- Wi-Fi 6 specific tuning
- Jetson CPU and memory profiling

Those values are environment-specific and should be tuned on real hardware instead of being guessed here.
