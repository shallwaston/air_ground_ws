# Mock 2.5D map tile message for UAV to UGV transfer tests.
# The arrays use primitive types on purpose to keep serialization simple and measurable.
std_msgs/Header header
float32 resolution
uint32 width
uint32 height
geometry_msgs/Pose origin
float32[] elevation
uint8[] traversability
builtin_interfaces/Time source_stamp
uint64 seq
