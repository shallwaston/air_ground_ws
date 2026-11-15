# Reviewed deployment and next implementation step

1. Review the complete R3-to-R8 diff and the smaller R7-to-R8 delta. Do not merge
   the inherited legacy runner wholesale or change the official branch by R8.
2. On the fixed Jazzy image, build ag_interfaces in a new prerequisite prefix with
   CMAKE_SKIP_RPATH=ON. Run scripts/prepare_strict_assets.py --interface-prefix
   <new-prefix>/ag_interfaces. It refuses an existing asset destination.
3. Build this candidate's seven packages. Use only /opt/ros/jazzy and its own
   install/local_setup.bash; never borrow old workspaces. Retain the generated
   manifest digest, source hashes, native/probe provenance and permissions.
4. Execute the absolute installed lib/ag_network_tools/ag_strict_isolated with
   --entry heartbeat_pub --output <unique-new-directory> --run-for 1.0. The
   interpreter must start with -IS; do not put an ambient Python wrapper before
   this launcher. Installed tf_healthcheck and ugv_map_tile_sub use the same
   fixed launcher and approved presets, not legacy console aliases.
5. To audit future client sources, produce a JSON {modules:{module:{path,sha256}}}
   under a reviewed root. Run the verified strict_dependency_gate.py with
   /usr/bin/python3 -I -S -B, --source-manifest, --entry-module and --output.
   Use CLIENT_BODY's exact cleanup template. Verify the checker itself against
   the reviewed release SHA before execution. Never replace failed results.
6. Future M6 implementation (separately authorized): first implement a small
   owned Session capability adapter and an ownership registry for that Session
   and evidence files. Do not create a generic signal manager or adopt PIDs.
   Add allocation, repeated close, concurrent misuse, original-error+cleanup,
   borrowed-resource, release-pin and call-graph negative tests before wiring
   one fixed heartbeat integration. DomainPool, Launch grandchildren and all
   other ROS entry migrations are separate changes, not prerequisites here.
7. Re-run exact 72/66/283 IDs and new integration tests before declaring real M6
   production integration. The 89 contracts and 141 lifecycle tests are subsets
   of 283. A passing simulation/client is not production integration. A separate
   authorization and system-level G5 proof is needed for five-topic DDS Smoke.

Rollback: discard this independent R8 candidate or restore its preserved pre-fix
source/asset records. Never reset the original work branch or any official ref.
All failed wrapper/query attempts and original counterexamples remain evidence;
use the final release manifest only after all final checks pass.
