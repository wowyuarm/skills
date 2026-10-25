#!/usr/bin/env python3
"""Mechanical gating for the skills repository.

Verifies that skill discovery, index files, and invocation declarations stay
consistent, so structure does not depend on discipline alone:

- skills live at skills/<group>/<name>/SKILL.md
- frontmatter carries name (matching the directory) and description
- every skill is indexed in its group README and the top-level README,
  and every indexed link resolves to a real skill
- User-invoked entries have disable-model-invocation: true; Model-invoked
  entries do not
- agents/*.yaml, when present, parses as a YAML mapping
- shell scripts parse under bash -n
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.M)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)\s*$", re.M)
DMI_RE = re.compile(r"^disable-model-invocation:\s*([^\s]+)\s*$", re.M)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.*?)\s*$", re.M)
USER_INVOKED = "user"
MODEL_INVOKED = "model"

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


class Skill:
    def __init__(self, path: Path):
        self.path = path
        self.dir = path.parent
        self.group = path.parent.parent.name
        self.name = path.parent.name
        self.errors: list[str] = []

    @property
    def rel(self) -> str:
        return f"{self.group}/{self.name}"

    def parse_frontmatter(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            self.errors.append("missing frontmatter block")
            return

        frontmatter = match.group(1)
        data: dict[str, object] = {}
        disable_model_invocation: str | None = None

        if yaml is not None:
            try:
                loaded = yaml.safe_load(frontmatter)
                if isinstance(loaded, dict):
                    data = loaded
                else:
                    self.errors.append("frontmatter did not parse to a mapping")
                    return
            except Exception as exc:
                self.errors.append(f"YAML parse error: {exc}")
                return
            value = data.get("disable-model-invocation")
            disable_model_invocation = None if value is None else str(value)
        else:
            name_match = NAME_RE.search(frontmatter)
            desc_match = DESCRIPTION_RE.search(frontmatter)
            dmi_match = DMI_RE.search(frontmatter)
            if name_match:
                data["name"] = name_match.group(1).strip().strip('"')
            if desc_match:
                data["description"] = desc_match.group(1).strip()
            if dmi_match:
                disable_model_invocation = dmi_match.group(1).strip()

        if not data.get("name"):
            self.errors.append("missing name")
        elif str(data["name"]) != self.name:
            self.errors.append(f"name mismatch: expected '{self.name}', got '{data['name']}'")
        if not data.get("description"):
            self.errors.append("missing description")

        if disable_model_invocation is not None and disable_model_invocation != "true":
            self.errors.append(
                f"disable-model-invocation must be 'true' when present, got '{disable_model_invocation}'"
            )
        self.invocation = USER_INVOKED if disable_model_invocation == "true" else MODEL_INVOKED

    def validate_side_files(self) -> None:
        agents_dir = self.dir / "agents"
        if agents_dir.is_dir():
            for meta in sorted(agents_dir.glob("*.yaml")):
                text = meta.read_text(encoding="utf-8")
                if yaml is not None:
                    try:
                        loaded = yaml.safe_load(text)
                        if not isinstance(loaded, dict):
                            self.errors.append(f"{meta.name} did not parse to a mapping")
                    except Exception as exc:
                        self.errors.append(f"{meta.name} YAML parse error: {exc}")
                elif not text.strip():
                    self.errors.append(f"{meta.name} is empty")

        scripts_dir = self.dir / "scripts"
        if scripts_dir.is_dir():
            for script in sorted(scripts_dir.rglob("*.sh")):
                proc = subprocess.run(
                    ["bash", "-n", str(script)], capture_output=True, text=True
                )
                if proc.returncode != 0:
                    detail = (proc.stderr or proc.stdout).strip()
                    self.errors.append(
                        f"shell parse failed for {script.relative_to(ROOT)}: {detail}"
                    )

        runtime_state = self.dir / "references" / "current-state.local.md"
        if runtime_state.exists():
            print(f"WARN {self.rel}: runtime state file present ({runtime_state.relative_to(ROOT)})")


def find_skills() -> list[Skill]:
    """Discover skills/<group>/<name>/SKILL.md and flag misplaced ones."""
    skills: list[Skill] = []
    misplaced: list[str] = []

    if not SKILLS_DIR.is_dir():
        return skills

    for group_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        for entry in sorted(group_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                skills.append(Skill(entry / "SKILL.md"))

    top_skill = SKILLS_DIR / "SKILL.md"
    if top_skill.is_file():
        misplaced.append(f"{top_skill.relative_to(ROOT)} (skills must live in skills/<group>/<name>/)")
    for group_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        direct = group_dir / "SKILL.md"
        if direct.is_file():
            misplaced.append(
                f"{direct.relative_to(ROOT)} (skill SKILL.md sits directly in a group directory)"
            )

    for path in misplaced:
        print(f"FAIL {path}")
        print(f"  - misplaced skill entry")

    return skills


def parse_index(readme: Path) -> tuple[dict[tuple[str, str], str], list[str]]:
    """Return indexed skills {(group, name): invocation} and dead-link errors."""
    indexed: dict[tuple[str, str], str] = {}
    errors: list[str] = []
    if not readme.is_file():
        return indexed, [f"missing index file: {readme.relative_to(ROOT)}"]

    invocation: str | None = None
    text = readme.read_text(encoding="utf-8")
    events: list[tuple[int, str, str]] = []
    for m in HEADING_RE.finditer(text):
        title = m.group(2).strip().strip(":")
        if title.lower() == "user-invoked":
            events.append((m.start(), "heading", USER_INVOKED))
        elif title.lower() == "model-invoked":
            events.append((m.start(), "heading", MODEL_INVOKED))
        else:
            events.append((m.start(), "heading", None))
    for m in LINK_RE.finditer(text):
        events.append((m.start(), "link", m.group(1)))
    events.sort()

    for _, kind, value in events:
        if kind == "heading":
            invocation = value
            continue
        target = (readme.parent / value).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            continue  # external links are not our business
        if target.name != "SKILL.md":
            continue
        if not target.is_file():
            errors.append(f"dead skill link in {readme.relative_to(ROOT)}: {value}")
            continue
        skill_dir = target.parent
        key = (skill_dir.parent.name, skill_dir.name)
        if invocation is None:
            errors.append(
                f"{readme.relative_to(ROOT)} links {value} outside a User-invoked/Model-invoked heading"
            )
            continue
        if key in indexed and indexed[key] != invocation:
            errors.append(f"{readme.relative_to(ROOT)} indexes {key[0]}/{key[1]} under both invocation kinds")
        indexed[key] = invocation

    return indexed, errors


def main() -> int:
    skills = find_skills()
    if not skills:
        print("No skills found under skills/.")
        return 1

    had_error = False

    print(f"Validating {len(skills)} skill(s) under {SKILLS_DIR.relative_to(ROOT)}/")
    print(f"PyYAML parser: {'available' if yaml is not None else 'unavailable; using basic checks'}")

    by_key: dict[tuple[str, str], Skill] = {}
    for skill in skills:
        skill.parse_frontmatter()
        skill.validate_side_files()
        by_key[(skill.group, skill.name)] = skill

    for skill in sorted(skills, key=lambda s: s.rel):
        if skill.errors:
            had_error = True
            print(f"FAIL {skill.rel}")
            for error in skill.errors:
                print(f"  - {error}")
        else:
            print(f"OK   {skill.rel} ({skill.invocation}-invoked)")

    # Index gating: group READMEs and the top-level README must match reality.
    group_dirs = sorted({p for p in SKILLS_DIR.iterdir() if p.is_dir()})
    for group_dir in group_dirs:
        indexed, errors = parse_index(group_dir / "README.md")
        actual = {(skill.group, skill.name): skill for skill in skills if skill.group == group_dir.name}

        for error in errors:
            had_error = True
            print(f"FAIL index {group_dir.name}/README.md")
            print(f"  - {error}")

        for key, invocation in indexed.items():
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

        missing = set(actual) - set(indexed)
        for key in sorted(missing):
            had_error = True
            print(f"FAIL index {group_dir.name}/README.md")
            print(f"  - missing entry for {key[0]}/{key[1]}")

    top_indexed, top_errors = parse_index(ROOT / "README.md")
    for error in top_errors:
        had_error = True
        print("FAIL index README.md")
        print(f"  - {error}")
    for key, invocation in top_indexed.items():
        skill = by_key.get(key)
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
    missing_top = set(by_key) - set(top_indexed)
    for key in sorted(missing_top):
        had_error = True
        print("FAIL index README.md")
        print(f"  - missing entry for {key[0]}/{key[1]}")

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
