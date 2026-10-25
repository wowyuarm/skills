#!/usr/bin/env python3
"""Check per-skill side files: agents/openai.yaml completeness, shell syntax,
runtime-state warnings."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_skills, yaml

INTERFACE_KEY_RE = re.compile(r"^\s+(display_name|short_description):\s*(\S.*)$", re.M)


def check_openai_yaml(skill) -> None:
    meta = skill.dir / "agents" / "openai.yaml"
    if not meta.is_file():
        skill.errors.append("missing agents/openai.yaml")
        return

    text = meta.read_text(encoding="utf-8")
    if yaml is not None:
        try:
            loaded = yaml.safe_load(text)
        except Exception as exc:
            skill.errors.append(f"agents/openai.yaml YAML parse error: {exc}")
            return
        if not isinstance(loaded, dict):
            skill.errors.append("agents/openai.yaml did not parse to a mapping")
            return
        interface = loaded.get("interface")
        if not isinstance(interface, dict):
            skill.errors.append("agents/openai.yaml missing 'interface' mapping")
            return
        for key in ("display_name", "short_description"):
            value = interface.get(key)
            if not isinstance(value, str) or not value.strip():
                skill.errors.append(f"agents/openai.yaml interface.{key} missing or empty")
    else:
        found = dict(INTERFACE_KEY_RE.findall(text))
        for key in ("display_name", "short_description"):
            if not found.get(key, "").strip():
                skill.errors.append(f"agents/openai.yaml interface.{key} missing or empty")


def check_shell_scripts(skill) -> None:
    scripts_dir = skill.dir / "scripts"
    if not scripts_dir.is_dir():
        return
    for script in sorted(scripts_dir.rglob("*.sh")):
        proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            skill.errors.append(f"shell parse failed for {script.name}: {detail}")


def main() -> int:
    skills, _ = find_skills()
    had_error = False

    for skill in sorted(skills, key=lambda s: s.rel):
        check_openai_yaml(skill)
        check_shell_scripts(skill)

        runtime_state = skill.dir / "references" / "current-state.local.md"
        if runtime_state.exists():
            print(f"WARN {skill.rel}: runtime state file present ({runtime_state.relative_to(skill.dir)})")

        if skill.errors:
            had_error = True
            print(f"FAIL {skill.rel}")
            for error in skill.errors:
                print(f"  - {error}")
        else:
            print(f"OK   {skill.rel} (openai.yaml complete, scripts parse)")

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
