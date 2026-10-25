#!/usr/bin/env python3
"""Check layout: every skill lives at skills/<group>/<name>/SKILL.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_skills


def main() -> int:
    skills, misplaced = find_skills()
    had_error = False

    for path in misplaced:
        had_error = True
        print(f"FAIL {path}")
        print("  - misplaced skill entry")

    if not skills:
        had_error = True
        print("FAIL skills/")
        print("  - no skills found under skills/")

    if not had_error:
        print(f"OK   layout: {len(skills)} skill(s) in {len({s.group for s in skills})} group(s)")
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
