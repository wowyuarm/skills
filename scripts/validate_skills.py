#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.M)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)\s*$", re.M)

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def find_skills(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def parse_frontmatter(skill_md: Path) -> tuple[dict[str, object], list[str]]:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, ["missing frontmatter block"]

    frontmatter = match.group(1)
    errors: list[str] = []
    data: dict[str, object] = {}

    if yaml is not None:
        try:
            loaded = yaml.safe_load(frontmatter)
            if isinstance(loaded, dict):
                data = loaded
            else:
                errors.append("frontmatter did not parse to a mapping")
        except Exception as exc:
            errors.append(f"YAML parse error: {exc}")
            return {}, errors
    else:
        name_match = NAME_RE.search(frontmatter)
        desc_match = DESCRIPTION_RE.search(frontmatter)
        if name_match:
            data["name"] = name_match.group(1).strip().strip('"')
        if desc_match:
            data["description"] = desc_match.group(1).strip()

    if not data.get("name"):
        errors.append("missing name")
    if not data.get("description"):
        errors.append("missing description")

    return data, errors


def validate_shell_scripts(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return errors
    for script in sorted(scripts_dir.rglob("*.sh")):
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            errors.append(f"shell parse failed for {script.relative_to(ROOT)}: {detail}")
    return errors


def main() -> int:
    skills = find_skills(ROOT)
    if not skills:
        print("No skills found.")
        return 1

    had_error = False
    print(f"Validating {len(skills)} skill(s) under {ROOT}")
    print(f"PyYAML parser: {'available' if yaml is not None else 'unavailable; using basic checks'}")

    for skill_dir in skills:
        skill_md = skill_dir / "SKILL.md"
        data, errors = parse_frontmatter(skill_md)
        expected_name = skill_dir.name
        actual_name = str(data.get("name", ""))
        if actual_name and actual_name != expected_name:
            errors.append(f"name mismatch: expected '{expected_name}', got '{actual_name}'")
        errors.extend(validate_shell_scripts(skill_dir))

        runtime_state = skill_dir / "references" / "current-state.local.md"
        if runtime_state.exists():
            print(f"WARN {skill_dir.relative_to(ROOT)}: runtime state file present ({runtime_state.relative_to(ROOT)})")

        if errors:
            had_error = True
            print(f"FAIL {skill_dir.relative_to(ROOT)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {skill_dir.relative_to(ROOT)}")

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
