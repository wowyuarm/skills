"""Claude Code store: ~/.claude/projects/<project-slug>/**/*.jsonl."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from itertools import islice
from pathlib import Path
from typing import Any

from .model import Turn, build_summary, iter_jsonl, mtime_utc, normalize_text, SessionSummary

PROJECTS_DIR = Path.home() / '.claude' / 'projects'
# The cwd fallback scans the whole store; bound it so huge stores stay fast.
FALLBACK_CANDIDATE_CAP = 200
INJECTED_USER_PREFIXES = (
    '<local-command-caveat>',
    '<local-command-stdout>',
    '<local-command-stderr>',
    '<command-name>',
    '<command-message>',
    '<command-args>',
    '<system-reminder>',
)


def derive_project_slug(project_path: Path) -> str:
    return '-' + str(project_path).strip('/').replace('/', '-')


def load_paths(project_dir: Path, project_path: Path, *, days: int, cap: int) -> list[Path]:
    """Recent JSONL files for the project: the slug directory first, then a
    bounded store-wide scan matched by cwd when the slug yields fewer than
    `cap` candidates (slug missing, sessions nested under subagent dirs, ...)."""
    if not PROJECTS_DIR.exists():
        raise FileNotFoundError(f'Claude projects directory not found: {PROJECTS_DIR}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    target = str(project_path)
    candidates: list[Path] = []

    if project_dir.exists():
        candidates = [path for path in project_dir.rglob('*.jsonl') if mtime_utc(path) >= cutoff]

    if len(candidates) < cap:
        seen = set(candidates)
        for path in PROJECTS_DIR.rglob('*.jsonl'):
            if path in seen or mtime_utc(path) < cutoff:
                continue
            if not _session_cwd_matches(path, target):
                continue
            candidates.append(path)
            if len(candidates) >= FALLBACK_CANDIDATE_CAP:
                break

    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[:cap]


def _session_cwd_matches(path: Path, target: str) -> bool:
    try:
        with path.open(encoding='utf-8', errors='replace') as handle:
            for _ in range(8):
                line = handle.readline()
                if not line:
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                cwd = record.get('cwd')
                if isinstance(cwd, str) and cwd:
                    return cwd == target or cwd.startswith(target + '/')
    except OSError:
        pass
    return False


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return normalize_text(content)
    if isinstance(content, list):
        parts = [
            block['text']
            for block in content
            if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str)
        ]
        return normalize_text('\n'.join(parts))
    return ''


def extract_turn(record: dict[str, Any]) -> Turn | None:
    record_type = record.get('type')
    timestamp = record.get('timestamp') or record.get('ts')

    if record_type in {'user', 'assistant'}:
        message = record.get('message')
        if isinstance(message, dict):
            text = _extract_text_from_content(message.get('content'))
            if text:
                if record_type == 'user' and text.startswith(INJECTED_USER_PREFIXES):
                    return None
                return Turn(role=record_type, text=text, timestamp=timestamp)
        return None

    if record_type == 'user_message':
        payload = record.get('payload')
        if isinstance(payload, dict) and isinstance(payload.get('content'), str):
            text = normalize_text(payload['content'])
            if text and not text.startswith(INJECTED_USER_PREFIXES):
                return Turn(role='user', text=text, timestamp=timestamp)
    return None


def read_metadata(path: Path) -> dict[str, str]:
    """cwd/gitBranch/model from the first records that carry each field."""
    out: dict[str, str] = {}
    for record in islice(iter_jsonl(path), 16):
        for key in ('cwd', 'gitBranch', 'model'):
            if key not in out and isinstance(record.get(key), str):
                out[key] = record[key]
        if {'cwd', 'gitBranch'}.issubset(out):
            break
    return out


def summarize(path: Path, keywords: list[str]) -> SessionSummary | None:
    turns: list[Turn] = []
    started_at: str | None = None
    for record in iter_jsonl(path):
        if started_at is None:
            started_at = record.get('timestamp') or record.get('ts')
        turn = extract_turn(record)
        if turn is not None:
            turns.append(turn)
    if not turns:
        return None
    metadata = read_metadata(path)
    return build_summary(
        'claude', path, turns, started_at, keywords,
        project_hint=metadata.get('cwd'),
        cwd=metadata.get('cwd'),
        git_branch=metadata.get('gitBranch'),
        model=metadata.get('model'),
    )
