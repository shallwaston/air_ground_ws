# Verified R1 development baseline

This branch starts exactly at `79c1a0fd48686fbecc267b3c2d54f378c96b2132`.
Its production files are unchanged. The only executable addition is the frozen
`test_node_runner_contract.py`; its SHA256 is
`7f738c21febc0fa3b05611a2e4c7fe5722cb4b3d2a47161c2f22ac87608d1b18`.
No manifest, dependency, ROS node, QoS, Topic, frame or message is changed.

## Evidence and version identity

The immutable R2 snapshot is commit
`9004a19610621ad062189dede8a988f8740acbaa` in the owner's private backup repository.
[R2 evidence and recovery page](https://github.com/shallwaston/air-ground-ws-backup-vault/tree/9004a19610621ad062189dede8a988f8740acbaa/r1/2026-11-15/r2-20261115T014019Z-6yt0_zxk).
Access requires that repository's authorization; no raw private logs or archives
are published on this branch.

- Source archive SHA256: `112fbc53ab1294db69d19f3cc0b7a3cb050e9ac7c8ec0d9d6b9f12cbc638b6c2`.
- Evidence archive SHA256: `ee9574000b42dc481f30ff254f4b8fc944c52fbcd062fa0b7fd8faedbfba6c75`.
- [Machine-readable index](validation/r1-baseline/evidence-index.json) contains
  all 283 unique canonical test IDs, immutable archive-relative evidence paths,
  file hashes and the original acceptance ranges.

R1 actually built seven packages; pytest passed 283 cases and colcon passed the
same 283 IDs. These are two runs of the same suite, not 566 different cases.
The 141 native lifecycle cases per run comprised 66 controlled timing cases,
42 installed-console SIGINT/SIGTERM cases across 21 entries, 18 signal-burst
cases, 10 expected failure-propagation cases and 5 compatibility/inventory cases.
The negative child exit1 observations are expected test evidence, not hidden
normal exits. The added 89-case file uses controlled rclpy doubles and is part
of the 283; it must not be counted as 89 additional native cases.

The independent safe adapter passed 77 cases and its controller 10 cases. Its
single real DDS Smoke exited0 and validated all five Topics, five 64x64 MapTile
payloads against actual source expressions/float32 and uint8 data, three TF
chains, and exactly16 independently bound child identities/clean exits.

## Runtime and reproducibility boundaries

Historical runtime: Ubuntu24.04.5, ROS2 Jazzy, Python3.12.3, rclpy7.1.12,
linux/amd64. Image ID:
`sha256:3e1ba97a2cda53301c6ba7e831e2c8506e54631f911c0bd26cfbc976479810c7`.
Image reference:
`ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617`.
ROS_DOMAIN_ID=42, RMW_IMPLEMENTATION=rmw_fastrtps_cpp,
ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST. A future environment needs its own
identity, CA, mount, resource, overlay and process-conflict admission checks.

For host-only contract checks, use Python3.12 and pytest in an isolated environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1   python3 -B -m pytest -p no:cacheprovider -q   src/ag_system_tests/test/test_node_runner_contract.py
```

Native revalidation is a separate authorized operation: load only the Jazzy
underlay in the reviewed environment, run `./scripts/build_ws.sh --parallel-workers 2`
in this new workspace, verify seven installation prefixes, load this workspace's
install overlay, collect test IDs, run pytest and colcon test/test-result while
retaining original results. Those ROS commands are not run by R3.

The independent Smoke has environment-bound paths and safety assumptions.
Retrieve its source and dependencies only from R2 for review; transplantation
requires a new equivalence and process-ownership admission. It is deliberately
not copied into this production repository or offered as an automatic command.

## Limits retained

Steady-state shutdown and controlled timing do not prove arbitrary-time early
SIGINT/S1 or process-wide multi-threaded signal-handler transitions. pidfd exit
readiness is independent, but child rc0 is a verified Launch direct-parent
report; the adapter is not those grandchildren's waitpid parent. Internal ROS
logs also existed under container ROS_HOME. Historical Git-log differences,
missing initial whole-.git hash, controller mis-stop and audit-format failures
remain in R2. No original failure evidence is rewritten.

M6 is not implemented or admitted by this baseline. ResourceScope, DomainPool,
ProcessProof, native_receive_adapter, historical M6 phases and the claimed117/243
counts require original evidence and a separately reviewed admission contract.
No PR is created, changed or merged by establishing this branch.

## R3 checks actually rerun

The unchanged89-case contract file was rerun in the independent official clone
on host Python3.12 with controlled rclpy doubles:89 passed,0 failed/skipped,
pytest exit0. Its canonical IDs exactly match the89 contract IDs inside the
historical283. Static checks covered56 Python files,7 manifests, an acyclic
internal dependency graph and21 main-to-runner entry mappings. R3 did not run
ROS native tests, colcon build/test or DDS Smoke; those results above are
immutable R1/R2 evidence. This host rerun is not an S1 or native-handle proof.
