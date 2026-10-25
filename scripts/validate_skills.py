#!/usr/bin/env python3
"""Aggregate runner: executes every scripts/checks/check_*.py and reports.

Each check is an independent script with its own exit code; this runner runs
them all and fails if any fails. Run a single check directly while iterating:

    python3 scripts/checks/check_frontmatter.py
"""
import subprocess
import sys
from pathlib import Path

CHECKS_DIR = Path(__file__).resolve().parent / "checks"


def main() -> int:
    checks = sorted(CHECKS_DIR.glob("check_*.py"))
    if not checks:
        print(f"No checks found under {CHECKS_DIR.relative_to(CHECKS_DIR.parent.parent)}.")
        return 1

    failed: list[str] = []
    for check in checks:
        print(f"== {check.stem}")
        sys.stdout.flush()
        proc = subprocess.run([sys.executable, str(check)])
        print()
        sys.stdout.flush()
        if proc.returncode != 0:
            failed.append(check.stem)

    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print(f"All {len(checks)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
