# R9 bounded OwnedSession candidate contract

Scope: one fixed `heartbeat_pub` direct child. This is an independent candidate,
not an official release, a general ProcessProof/ResourceScope, DomainPool, or G5.
Legacy S1 and its five historical failures remain unchanged and BLOCKED.

## Approved production path

`m6_fixed_heartbeat.FixedHeartbeatAdapter` →
`m6_owned_session.OwnedSessionRegistry` →
`strict_entry.create_session(heartbeat_pub, ..., acquisition_receipt=...)` →
existing `IsolatedSession` → trusted exec / private BIRTH_ACK / READY / START →
existing authenticated pidfd SIGINT → original direct waitpid → registry report.

The adapter accepts only a unique output directory, an explicit final release
SHA256, and an optional borrowed parent Context object. No arbitrary entry,
Node, argv, PID, signal number, closer, timeout expansion, or automatic retry is
accepted. Only the existing strict backend emits signals or reaps the child.
There is no independent short-lived MVP console: a supervised creator must stay
alive while an uncertain responsibility remains. `ag_strict_isolated` remains
the reviewed source-only loader and existing strict console, not a hidden legacy
entry replacement. All original 21 business consoles remain unchanged.

## Supported admission

Controlled Linux/Jazzy Python 3.12 fixed image; exact root-protected dependency
set; verified source-only loader; private child Context, SingleThreadedExecutor,
synchronous callbacks; exact creator process and main Thread object. The source
policy SHA and deployment manifest must match. A supervisor must acquire the
nonblocking Smoke lock, perform full namespace process visibility/conflict
checks, and keep this admission exclusive. The in-interpreter one-slot lock is
only an ownership budget, not a process-wide signal lock or DDS domain lease.
A noncooperating external writer, hidden process, creator death, arbitrary
thread/handler sharing in the strict child, and unsupported platform are outside
this bounded contract. Existing parent handlers/threads can remain borrowed;
they are never adopted or changed. Foreign SIGCHLD/reapers are rejected where
observable; if a reaper takes over later, missing actual raw status is failure.
Early process startup before READY retains the documented OS-exit/supervisor
responsibility boundary; this is not arbitrary-time S1 safety.

## Ownership and transitions

OWNED: opaque acquired strict Session, direct-child supervision/reap duty,
unique evidence journal, registration receipt/state. BORROWED: domain 42,
container/image, parent Context, handlers, threads, processes, other ROS/DDS.
Borrowed resources have no cleanup callbacks and no shutdown/release edges.

`NEW → ACQUIRING → READY → RUNNING → STOP_REQUESTED → REAPED → CLOSING → CLOSED`.
Any unproven reference/journal cleanup leads to `QUARANTINED`. One provisional
receipt is bound before backend constructor side effects, but an empty receipt
is not invented process ownership. Registration commits once after authenticated
identity, fixed entry/release, READY and live private Context query. A second
live/uncertain registry is rejected. A strong owner reference retains unresolved
duty; dropping the user's adapter reference does not count as cleanup.

Close independently attempts only applicable stop/wait/reference/journal work.
It records each exception, preserves original objects and tracebacks in
BaseExceptionGroup, retires uncertain descriptors/resources rather than blindly
retrying, and is idempotent. Repeat close repeats no destructive operation.
After a failed wait there is no automatic production retry. The already existing
strict failure-abort capability may use SIGTERM as explicit failed supervision
cleanup; this always remains a failed acceptance, never normal PASS. No SIGKILL,
numeric PID/PGID signal fallback, second sender or reaper is added. Unknown
identity prohibits further stop/abort. A responsible supervisor can obtain the
retained opaque capability only for a QUARANTINED registry; manual recovery is
separate from and must not rewrite the sealed failed verdict.

CLOSED means owned cleanup is proven. It does not itself mean application PASS:
normal acceptance additionally requires actual user START, at least one complete
callback, strict acceptance, raw child wait status 0, no errors, no recovery,
and no outstanding responsibility. A timeout, foreign reap, unproven close, or
child nonzero result can never be converted to normal acceptance by a parent
exit code 0 or pidfd readiness.

## Evidence and integrity

Reports record creator PID/native TID, generation, child birth identity,
nonce digest, exact release, receipt, READY/registration, stop/wait attempts,
actual raw wait status, each owned/borrowed resource, error trees, outstanding
duty, and slot retention. A private journal is opened exclusively in a new
0700 directory and stored 0600. Generation nonces are local identifiers, not
credentials. Caller output is an operator-approved new directory, not a
security sandbox against a hostile same-UID filesystem writer.

The pinned `_m6_mvp_policy.json` binds exact reviewed module bytes. Static call
review additionally rejects legacy signal paths, arbitrary dynamic imports,
new low-level signals/reapers, native/new-thread hooks and borrowed closers.
It is a closed reviewed graph for this candidate, not a universal Python proof.
Official repository CI / branch enforcement: **NOT DEPLOYED**.

## Native acceptance boundaries

A real positive trial must use the unpatched installed verified production
API and actual DDS Heartbeat subscriber. Fault workers are explicitly labelled
injections; their expected rejection PASS is never normal child acceptance.
All original R6/R7/R8 conditions and 283 unique baseline IDs must be retained.
The 89 contract and 141 lifecycle IDs are subsets and are not added to 283.
The final 283 run must be linked to final source/policy/asset hashes. No G5 Smoke
or official production publication is authorized in R9.
