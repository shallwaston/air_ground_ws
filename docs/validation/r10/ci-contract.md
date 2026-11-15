# CI contract and remaining deployment work

## Non-ROS Actions

`M6 static admission` runs on GitHub-hosted ubuntu-24.04 for this M6 branch and
pull requests targeting r2/r1-verified-baseline. Only contents:read is granted;
there is no pull_request_target, secret expression, self-hosted runner, ROS job,
Docker invocation/socket mount, dependency installation or automatic pin update.
Checkout credentials are not persisted, submodules/LFS are disabled and full
local history is fetched so diff --check covers R3..HEAD, not an empty tree.

The two official Actions are resolved from actual releases/tags and SHA-pinned:

- actions/checkout v7.0.1: `3d3c42e5aac5ba805825da76410c181273ba90b1` (Node24).
- actions/upload-artifact v7.0.2: `cf430e030ddbb5b0abf93d22962f4752f3646cd9` (Node24).

Publisher identity/tag/entry metadata were checked. A commit pin prevents tag
drift, not every publisher/supply-chain compromise; no claim of a full audit of
all bundled JavaScript is made. These pinned managed Actions alone access their
read-only checkout/artifact service credentials. No credential is passed to
repository test code. The host uploader never consumes an untrusted output directory. A separate
unprivileged literal reader checks a single regular, same-owner, single-link,
bounded JSON through O_NOFOLLOW/NONBLOCK and stable fstat, then exports data to
a new host-owned file. Symlink/hardlink/FIFO/size/schema/foreign-owner and import
surface controls actually execute. Artifact retention is14 days; actual run logs/results are
separately preserved in the R10 audit. No artifacts overwrite earlier runs.

GitHub's host runner is an administrable VM; this contract does not call that
entire VM unprivileged. Only literal inline setup commands use sudo to copy input
without dereferencing links, create PID/mount/network namespaces, mask /run and
drop to UID/GID65532 with no supplementary groups, empty capabilities, and
no_new_privs. No repository script executes before that drop. env -i passes only
PATH/LANG/HOME/TMPDIR. Input is root-owned and readonly to tests; output is owned
by65532. The actual checker requires/records this profile, no Docker socket, only
loopback, no credential environment, and no residual namespace child. Missing
namespace/capability conditions fail the job; there is no weaker CI fallback.

The original R9 hash inventory plus the explicit R10 format-only release overlay,
fixed policy, closed call graph,
legacy isolation in the new path, original21 targets, XML/DAG, syntax/AST,
211 historical oracle IDs and original283 IDs are checked. The unchanged 59
non-ROS R9 tests really execute. Missing ROS/native tests are NOT EXECUTED, not
skipped-and-counted PASS. Original R9 native9 are separate native validations.
`m6_static.py` local mode clearly labels the GitHub sandbox NOT EXECUTED.

A workflow file is not CI PASS. Consult the actual run ID, head commit, job/steps,
logs, result artifact and command exits. Branch protection/rulesets are separate;
this task does not configure mandatory status enforcement.

## Operator-only native plan — NOT DEPLOYED on GitHub

`m6_native_worker.py` provides build, collect, regress, mvp-positive and mvp-faults
phases. It requires R10_NATIVE_AUTHORIZED=1 and a mode0600 same-UID exact host
admission receipt/hash. It refuses absent authorization with77 before any work.
That receipt is a trusted supervisor record, not a standalone cryptographic
proof against a malicious caller. No GitHub workflow invokes this native worker.
No self-hosted runner is created or registered and the Cloud container is never
exposed to GitHub Actions.

A separately authorized host supervisor must verify and retain control of:

- Managed socket unix:///var/run/docker.sock; original container
  a726e9d27fc88c3c01ad64379cd230c38208e4aadfbf5c595392353e987d79b2.
- Image ID sha256:3e1ba97a2cda53301c6ba7e831e2c8506e54631f911c0bd26cfbc976479810c7;
  ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617;
  linux/amd64, exact original config/UID/GID1000/mounts/init/environment.
- Existing RW /workspace and RO CA; domain42, rmw_fastrtps_cpp, LOCALHOST;
  no unknown DDS overrides, no paused/restarting/dead state, adequate bytes/inodes.
- Nonblocking Smoke flock with inode/link/type proof, complete process visibility
  and no competing DDS/launch or unknown exec users; repeat between phases.

The worker clears inherited overlays, sources only Jazzy and its own install,
requires fresh build/install/log, builds seven packages with two workers,
verifies seven prefixes/21 consoles and exact original283 collection, then runs
283 plus real fixed-heartbeat production API and eight controlled native faults.
Validation-only pidfd transport is byte-identical R9 test code, scoped to the
legacy regression process; no second production sender/reaper is introduced.
There is no G5, dependency install, source/pin edit, cache deletion, timeout
expansion, automatic retry or SIGKILL success path. Stop on a failed phase.

Before stopping a task-started original container, the trusted host must verify
all known children reaped, complete namespace quiet, unchanged ID/config and own
StartedAt, no unknown exec user, and released lock. Restore exited only when safe;
otherwise retain it and report unresolved responsibility. Native CI cannot be
called deployed until an independently authorized runner/admission/supervision
and enforcement arrangement actually satisfies this contract.

Before any candidate import, the checker refuses source symlinks, unapproved/tampered bytecode and undeclared Python/native/startup modules in source import roots.
This complements (and does not replace) the R9 source-only production loader.
Git diff disables external/textconv callbacks. Local subprocess environments
are explicitly limited; GitHub test environment is empty apart from named
nonsecret runtime paths. This does not claim to prevent a reviewer-approved
future workflow change from changing its own policy; review and enforcement
remain necessary and are not configured by this task.

R3/R9 already track44 historical .pyc files. They remain exact frozen data, not
import authority; deleting them would change the approved source snapshot. The
first stricter draft guard rejected those inherited files and its failure is
retained. Final admission allows only their exact original hashes and forbids
unknown/tampered caches. All59 original offline cases now boot through a
CI-only source finder that compiles manifest-pinned Python bytes and refuses the
legacy module; no pyc is used. The34 original worker cases/order/inputs/assertions
are preserved with actual source-bootstrap argv/exits recorded. The original
run_unit.py is unchanged. Independent controls prove a valid poison .pyc actually
executes in an ordinary import and is ignored by the CI source bootstrap. This
changes validation bootstrapping, not production code, test assertions or rounds.

## Reviewed R10 format-only release overlay

Complete staged diff --check found an extra trailing LF in original R9
m6_fixed_heartbeat.py. The original R9 candidate, pin, archives and successful
runtime records remain intact. A second independent clone removes exactly one
LF; its Python AST is identical. The associated policy-hash constant and bound
release metadata/source ZIP are updated as one explicit, reviewed seven-file
overlay in release-migration.json. This is not an automatic repin on CI or a
claim that changed bytes still match the original R9 fingerprint. Native binaries,
entry presets, scopes, imports/call behavior and all original assertions/rounds
are unchanged. 269 original files are byte-identical; 7 have the declared coupled
release delta. Native build/283/heartbeat9 must be rerun for the new release.

Original R9 release: `7dc7ebc4a9a5c42f3dcbec6cf4e3bdfb240dcf16dac863370fee4c5e6fd5e8fa`.
Reviewed R10 release: `b7d8299e006c4e9fc9e75dfd0db5da32abb7a48f26bf997083b1400136b32e3b`.
Reviewed R10 policy: `dad0eb9f807aacc2039e29e53db2f43a539c11353de05a15dfcb38594b1a028c`.
The checker independently reconstructs this limited data/source difference and
compares original source, policy and manifest records; it never generates pins.

The original one-LF-different heartbeat source is stored losslessly as base64
in r9-origin, so the complete Git whitespace check need not be disabled for an
exact historical counterexample. Decoding is checked against the original R9
SHA256. Static/native admission verifies all276 frozen source/data records;
the source-only test loader ignores44 inert bytecode objects by design and
independently authenticates the source it compiles. The poison-cache control
executes the poison in the ordinary-import control before proving source-only
execution ignores that same valid cache. Native results for the reviewed R10
release are indexed in native-results-index.json; these are actual controlled
Cloud executions, not GitHub Actions executions.
