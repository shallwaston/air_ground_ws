#!/usr/bin/env python3
"""Local CI check, no Docker/ROS import, no official CI deployment implied."""
import argparse,json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    package=a.source_root.resolve()/'src/ag_network_tools/ag_network_tools';path=package/'strict_dependency_gate.py'
    # Compile the exact reviewed checker bytes, never an ambient module or pyc.
    namespace={'__name__':'m6_admission_ci','__file__':str(path)}
    exec(compile(path.read_bytes(),str(path),'exec'),namespace)
    report=namespace['audit_mvp_package'](package);a.output.write_text(json.dumps(report,indent=2)+'\n');return 0
if __name__=='__main__':raise SystemExit(main())
