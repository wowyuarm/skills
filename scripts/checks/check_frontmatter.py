#!/usr/bin/env python3
"""Check SKILL.md frontmatter: name, description, invocation declaration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import MODEL_INVOKED, USER_INVOKED, find_skills, yaml


def main() -> int:
    skills, _ = find_skills()
    had_error = False
    print(f"PyYAML parser: {'available' if yaml is not None else 'unavailable; using basic checks'}")

    for skill in sorted(skills, key=lambda s: s.rel):
        skill.parse_frontmatter()
        if skill.errors:
            had_error = True
            print(f"FAIL {skill.rel}")
            for error in skill.errors:
                print(f"  - {error}")
        else:
            print(f"OK   {skill.rel} ({skill.invocation}-invoked)")

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
