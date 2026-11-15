# Bounded M6 development candidate, not a production-wide S1 approval

The original R9 source and deployable capsule were restored from the independently
re-downloaded Private freeze commit `5f095480cea2ce5d4c5a9f6e5db7dc79ae99d1d2`.
The formal starting commit is R3 `2781146abcebf04d9470eb9627098be077cbb2ee`.
`r9-provenance.json` binds every one of the 276 original source/assets files and
the original 21 console targets. The final R10 release has the explicit seven-file
format-only overlay below; all assertions, test IDs and rounds are unchanged.

## Layer review

| Layer | Files / responsibility | Admission and limit |
|---|---|---|
| A, R6/R7 controlled exec | isolated_probe, isolated_bootstrap, isolated_runtime, isolated_resources, isolated_runner | Trusted fresh exec, birth nonce/READY/START, private Context and executor, existing pidfd/direct waitpid. The exact tested source is retained. |
| B, R8 source/entry/dependency protection | isolated_entries, isolated_assets, strict_entry, strict_dependency_gate, bound ag_strict_isolated bootstrap | Existing three opt-in pilot presets are unchanged. No arbitrary Node/argv, overlay, dynamic client imports, or numeric signal fallback is added. |
| C, R9 MVP | m6_fixed_heartbeat, m6_owned_session, _m6_mvp_policy; minimal receipt/allocation fixes in facade/backend | One fixed heartbeat direct child; same creator; typed creation receipt; one registration; actual raw wait; independent owned journal cleanup; quarantine retains duty. No second sender or reaper. |
| D, inherited resource cleanup | isolated_resources and resource portions of legacy node_runner | Strict child uses the extracted resource module, never the legacy signal scope. Partial executor/node cleanup and exception preservation are retained. |
| E, legacy compatibility, NOT admitted | actual node_runner.py, especially _stop_signals, native/Python handler restore and default-context fallback | Five original foreign-ownership failures remain BLOCKED. This file is retained for the existing 21 consoles and historical 283 regression, not certified as safe for M6. |
| F, tests/docs/package data | unchanged R9 tests, pinned original regression transport, validation scripts, manifest, source.zip, native capsule and generated launcher | Native data retain the exact R9 Jazzy ABI; source capsule metadata use the reviewed R10 overlay. No pin regeneration occurs on CI or checkout. Native ABI execution is separate from static integrity. |

The immutable release couples source hashes, MVP policy, source ZIP, native
capsule and bound loader across A/B/C/D/F. These are delivered as one atomic
runtime commit, rather than incomplete intermediate commits with missing or
mismatched pins. CI/operator validation and this review are a separate commit.
This is dependency-based layering, not a claim of five independently releasable
features. No official base branch or previous PR is changed.

## Strict versus legacy

The child ZIP excludes `ag_network_tools/node_runner.py`. In the controlled child,
`isolated_runtime.run_ros` installs an explicit module bridge with origin
`strict-approved-entry-bridge`; it exposes only a class-checked strict_driver and
strict resource stop. Attempts to obtain the legacy signal API are refused.
The real business main is called once with its approved Node class and private
Context. The resource module contains no import of the real legacy runner.
The parent MVP imports only the reviewed strict facade; all low-level identity,
signalling and waitpid authority remains in the original strict backend.
Hashing the legacy source for provenance does not grant permission to execute it.

The 21 original console_scripts targets and business sources are unchanged.
Their shared legacy lifecycle utility differs from R3, inherited exactly from
R9 and explicitly classified D/E here. None of those consoles is silently changed
to spawn the new mode. M6 uses an explicit lifetime-owning FixedHeartbeatAdapter
API, not an autonomous short-lived CLI. Unresolved responsibility must remain
supervised; abandoning the creator is unsupported.

No Topic, QoS, frame, Heartbeat field, frequency/preset, message definition,
Node/entry allowlist or production import/call edge has changed relative to R9.
No DomainPool, generic ResourceScope/ProcessProof, extra process, M5, cross-device
communication, production retry, signal manager or independent G5 is introduced.

## Acceptance interpretation

The R9 historical 283, 68, 72/66/73 and heartbeat raw0 evidence remain labelled
historical in their provenance index. R10 actual runs have separate records.
The 89 contract and 141 lifecycle IDs are subsets of 283, never added again.
A static Actions PASS does not mean ROS ran on GitHub. Native ROS CI is NOT
DEPLOYED. Required branch status enforcement is NOT CONFIGURED by this change.
Legacy S1 remains BLOCKED/UNCHANGED; G5 is NOT EXECUTED. A new branch or Draft PR
is a review candidate, not permission to merge or a full production acceptance.

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
