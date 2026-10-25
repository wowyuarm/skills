"""Shared helpers for the atomic checks in this directory.

Every check script imports from here so skill discovery, frontmatter
parsing, and index parsing stay defined in exactly one place.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
        self.invocation: str = MODEL_INVOKED

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
            # YAML parses an unquoted true into a bool; accept both forms.
            disable_model_invocation = None if value is None else str(value).lower()
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


def find_skills() -> tuple[list[Skill], list[str]]:
    """Discover skills/<group>/<name>/SKILL.md plus a list of misplaced ones."""
    skills: list[Skill] = []
    misplaced: list[str] = []

    if not SKILLS_DIR.is_dir():
        return skills, misplaced

    top_skill = SKILLS_DIR / "SKILL.md"
    if top_skill.is_file():
        misplaced.append(
            f"{top_skill.relative_to(ROOT)} (skills must live in skills/<group>/<name>/)"
        )
    for group_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        direct = group_dir / "SKILL.md"
        if direct.is_file():
            misplaced.append(
                f"{direct.relative_to(ROOT)} (skill SKILL.md sits directly in a group directory)"
            )
        for entry in sorted(group_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                skills.append(Skill(entry / "SKILL.md"))

    return skills, misplaced


def parse_index(readme: Path) -> tuple[dict[tuple[str, str], str], list[str]]:
    """Return indexed skills {(group, name): invocation} and dead-link errors."""
    indexed: dict[tuple[str, str], str] = {}
    errors: list[str] = []
    if not readme.is_file():
        return indexed, [f"missing index file: {readme.relative_to(ROOT)}"]

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

    invocation: str | None = None
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
            errors.append(
                f"{readme.relative_to(ROOT)} indexes {key[0]}/{key[1]} under both invocation kinds"
            )
        indexed[key] = invocation

    return indexed, errors
