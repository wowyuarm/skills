#!/usr/bin/env python3
"""Check index files: group READMEs and the top-level README match reality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SKILLS_DIR, ROOT, Skill, find_skills, parse_index


def check_group_readme(skills: dict[tuple[str, str], Skill], group_dir: Path) -> bool:
    had_error = False
    indexed, errors = parse_index(group_dir / "README.md")
    actual = {k: v for k, v in skills.items() if k[0] == group_dir.name}

    for error in errors:
        had_error = True
        print(f"FAIL index {group_dir.name}/README.md")
        print(f"  - {error}")

    for key, invocation in sorted(indexed.items()):
        skill = actual.get(key)
        if skill is None:
            had_error = True
            print(f"FAIL index {group_dir.name}/README.md")
            print(f"  - links {key[0]}/{key[1]} which does not exist in this group")
            continue
        if skill.invocation != invocation:
            had_error = True
            print(f"FAIL index {group_dir.name}/README.md")
            print(
                f"  - lists {key[1]} as {invocation}-invoked but frontmatter says {skill.invocation}-invoked"
            )

    for key in sorted(set(actual) - set(indexed)):
        had_error = True
        print(f"FAIL index {group_dir.name}/README.md")
        print(f"  - missing entry for {key[0]}/{key[1]}")

    return had_error


def check_top_readme(skills: dict[tuple[str, str], Skill]) -> bool:
    had_error = False
    indexed, errors = parse_index(ROOT / "README.md")
    for error in errors:
        had_error = True
        print("FAIL index README.md")
        print(f"  - {error}")
    for key, invocation in sorted(indexed.items()):
        skill = skills.get(key)
        if skill is None:
            had_error = True
            print("FAIL index README.md")
            print(f"  - links {key[0]}/{key[1]} which does not exist")
            continue
        if skill.invocation != invocation:
            had_error = True
            print("FAIL index README.md")
            print(
                f"  - lists {key[0]}/{key[1]} as {invocation}-invoked but frontmatter says {skill.invocation}-invoked"
            )
    for key in sorted(set(skills) - set(indexed)):
        had_error = True
        print("FAIL index README.md")
        print(f"  - missing entry for {key[0]}/{key[1]}")
    return had_error


def main() -> int:
    skills_list, _ = find_skills()
    for skill in skills_list:
        skill.parse_frontmatter()
    skills = {(skill.group, skill.name): skill for skill in skills_list}

    had_error = False
    for group_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        had_error = check_group_readme(skills, group_dir) or had_error
    had_error = check_top_readme(skills) or had_error

    if not had_error:
        print(f"OK   indexes: {len(skills)} skill(s) covered in group and top-level READMEs")
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
