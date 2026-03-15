"""Central topic and frame names used across the workspace.

Keeping these names in one place makes it easier to replace mock nodes with
real adapters later without hunting through many files.
"""

HEARTBEAT_TOPIC = "/system/heartbeat"
DELAY_PROBE_TOPIC = "/system/delay_probe"
DELAY_REPORT_TOPIC = "/system/delay_report"

UAV_ODOM_TOPIC = "/uav/odom"
UAV_MAP_TILE_TOPIC = "/uav/map/tile"
UAV_TARGET_TOPIC = "/uav/targets/current"

TF_TOPIC = "/tf"
TF_STATIC_TOPIC = "/tf_static"

FRAME_MAP = "map"
FRAME_UAV_BASE = "uav/base_link"
FRAME_UGV_ODOM = "ugv/odom"
FRAME_UGV_BASE = "ugv/base_link"

KEY_TOPICS = [
    HEARTBEAT_TOPIC,
    DELAY_PROBE_TOPIC,
    UAV_ODOM_TOPIC,
    UAV_MAP_TILE_TOPIC,
    UAV_TARGET_TOPIC,
]

KEY_FRAMES = [
    FRAME_MAP,
    FRAME_UAV_BASE,
    FRAME_UGV_ODOM,
    FRAME_UGV_BASE,
]
