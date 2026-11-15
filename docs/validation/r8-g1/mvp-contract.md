# R8: limited S1 interface and proposed M6 MVP

This is a design and executable-admission candidate, not M6 production integration.
The official starting commit is 2781146abcebf04d9470eb9627098be077cbb2ee.
R7 is permanently preserved at Private backup commit
ba7b18876647c105739467598c956bface78f8dd under
s1-evidence/2026-11-15/r8-20261115T182110Z-h6vdp1di/r7-freeze.

## Existing code and proposed code

Existing: strict_entry -> RuntimePolicy/deployment assets -> controlled exec ->
sealed bootstrap -> private READY/START -> private Context and
SingleThreadedExecutor -> one approved pinned Node -> independent cleanup;
parent retains one creator thread, original proc anchor, pidfd and direct waitpid.
The business module's node_runner import is intercepted only in the verified
child by the fixed strict bridge. The legacy file is excluded from the sealed
source ZIP. Hashing its compatibility source does not admit its signal manager.

Proposed only: ProcessProof MVP delegates to this owned opaque Session;
ResourceScope owns that Session and its evidence, never arbitrary existing PIDs,
Launch grandchildren, parent Contexts or foreign handlers. Neither module exists
as new production code here. DomainPool is independently deferred: fixed Domain
42 is borrowed, never allocated or released. One supervised instance, existing
managed container, LOCALHOST, nonblocking exclusive lock and complete process
scan are required. A local flock is not proof of network-wide DDS exclusivity.

One fixed heartbeat_pub configuration suffices for the declared ROS integration
pilot. tf_healthcheck and ugv_map_tile_sub remain optional already checked strict
pilots. The other 18 legacy consoles are not needed by this minimal design;
future requirements for them, arbitrary parameters, Launch, cross-machine DDS,
parallel sessions, async callbacks or new worker/reaper threads require a new
contract and new admission. Kernel-only identity algorithms need no ROS console.
No future M6 layer may add a signal manager or a second Context/reaper owner.

## Executable source and release boundary

strict_dependency_gate admits only the reviewed closed module graph, static
aliases/re-exports and exact fixed exception-cleanup template. It refuses unknown
imports, reflection/dynamic dispatch, arbitrary Node/configuration, legacy calls,
PID/PGID signalling and unbound release identity. Approved source is hash-checked
before trusted execution. This is deliberately a narrow CI/deployment grammar,
not a sandbox or a proof about arbitrary Python. Future production modules must
be present, exhaustively listed and reviewed; checking this test client cannot
prove their integration. CI enforcement must itself be required by the future
branch/release process; it is not installed on the official remote by R8.

The fixed installed executable starts /usr/bin/python3 -IS before Python package
imports. It is installed as an executable data file, avoiding setuptools' ambient
pkg_resources development wrapper. Its generated immutable release digest binds
the package sources, C probe, sealed ZIP, six native interface objects and fixed
Jazzy interpreter. PYTHONPATH, sitecustomize and ROS overlay contamination are
ignored by that entry; a different package/release or unsafe/missing asset is
refused before spawning a ROS child. API use requires a trusted parent import
origin and the reviewed expected_manifest_sha256. An API cannot undo hostile
code already executed in its parent. A root/same-UID adversary or hostile loader
variables at interpreter birth are outside this controlled deployment contract.

## Lifecycle and exception rules

The same parent thread alone owns each Session. A child is signalable only after
its authenticated birth and identity proof, using pidfd; never numeric fallback.
Early signals before managed READY may produce ordinary OS/nonzero exit. After
READY, only synchronous callbacks and the private SingleThreadedExecutor are
supported. Known ROS native threads arise after controlled signal handoff; this
is not a claim that the whole ROS process remains single-threaded. Foreign child
owners are refused or detected and never restored over. Non-cooperating native
writers are not claimed to coexist safely. Parent foreign Python/C handlers and
threads are borrowed and preserved; foreign SIGCHLD/reapers remain unsupported.

The exact client template preserves a primary exception and all abort/reference
cleanup failures in BaseExceptionGroup, with the owned capability attached if
cleanup fails. Failed supervision is never normal acceptance. Close is not a
substitute for wait; a live unreaped child cannot be silently closed. Callback
return, executor shutdown, Node destruction and shutdown/destroy of the same
private Context precede accepted exit. Direct raw wait status, not a parent's
zero status or pidfd readiness alone, proves the direct child's result.

R8 fixes two existing strict protocol defects found by the new call path: consume
complete QUERY commands already buffered behind START, and apply the existing
query timeout to the whole operation rather than each telemetry packet. No retry
or larger timeout is introduced. Original counterexamples remain in R8 evidence.
Legacy S1's five R4 failures remain BLOCKED/UNCHANGED.

## Decision limits

A passing S1 boundary applies only to this fixed controlled interface. MVP design
admission can be CONDITIONAL on future immutable source/deployment CI and actual
M6 integration tests. M6 production integration is NOT EXECUTED. Historical
Phase2/3A/3B, native_receive_adapter and 117/243 claims remain UNKNOWN. G5 and the
independent five-topic system Smoke are separate and NOT EXECUTED by R8.
