# Local CI and operator revalidation

Official CI enforcement is NOT DEPLOYED. No workflow, remote branch or branch
protection is changed here. A future authorized baseline change must independently
review this graph, negative tests, native release and deployment permissions.

Without ROS/Docker, from a restored candidate directory:

```bash
python3 -B scripts/check_m6_mvp_admission.py --source-root "$PWD" --output /approved/new/admission.json
python3 -B validation/m6_mvp1/run_unit.py /approved/new/unit-results
python3 -B validation/m6_mvp1/test_acquisition_receipt.py /approved/new/receipt-results
python3 -B validation/m6_mvp1/test_dependency_review.py /approved/new/dependency-results
python3 -B validation/m6_mvp1/test_policy_identity.py /approved/new/policy-results
```

Inspect each script's actual CLI before execution; outputs must be unique and
retained. Never repin sources automatically merely to make a CI check pass.
The authority pin writer is a development review tool outside the candidate,
not a runtime or CI policy updater. Generator refuses to replace an existing
strict_assets destination. Preserve any superseded R9 iterations as evidence.

Native work requires separately authorized fixed-container admission, same
original image/container/UID/mount/environment, exclusive lock, full visible
process scan and own candidate install overlay. Clear inherited AMENT/CMAKE/
COLCON/PYTHONPATH/LD/ROS_PACKAGE_PATH before sourcing Jazzy and candidate only.
Use `./scripts/build_ws.sh --parallel-workers 2` in this candidate. Verify all
seven package prefixes and original 21 consoles resolve inside it.

The positive native harness `validation/m6_mvp1/native_heartbeat.py` is run with
`python3 -I -S -B <absolute-script> <unique-output>`. It invokes the exact installed
`ag_strict_isolated` verified loader, then the actual unpatched production API.
It creates its own separate subscriber Context/Node/Executor, borrows that Context
to the adapter, and after the MVP report separately cleans its own probe. It is
not a replacement business node, test extension, or mocked factory. Installed
paths in the script are derived from the candidate, not original /workspace
history. Negative native workers may inject faults only into their own test
process and owned capabilities; those results are explicitly not normal exits.

A final full original 283 native run must occur after source and deployment
bytes stabilize. Capture source SHA list, policy, capsule, launcher, manifest,
collection ID set and original signal audit. If runtime code/assets change,
retain earlier results and reassess/re-run before final acceptance. Historical
R8 full-283 manifest and its later final release are distinct evidence stages.
No inherited R8 result can stand in for R9 final bytes.

Finish by proving known children reaped, all namespaces quiet, borrowed state
unchanged, lock released, same original container/config restored exited, and
all protected original work/Git/helper/archive/remote evidence unchanged.
