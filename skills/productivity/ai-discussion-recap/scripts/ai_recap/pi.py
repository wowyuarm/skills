"""Pi store: ~/.pi/agent/sessions/<project-slug>/*.jsonl."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .model import Turn, build_summary, iter_jsonl, mtime_utc, normalize_text, SessionSummary

SESSIONS_DIR = Path.home() / '.pi' / 'agent' / 'sessions'


def derive_project_slug(project_path: Path) -> str:
    return f'--{str(project_path).strip("/").replace("/", "-")}--'


def load_paths(project_path: Path, *, days: int, cap: int) -> list[Path]:
    if not SESSIONS_DIR.exists():
        raise FileNotFoundError(f'Pi sessions directory not found: {SESSIONS_DIR}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    slug_dir = SESSIONS_DIR / derive_project_slug(project_path)
    paths: list[Path] = []

    if slug_dir.exists():
        paths = [path for path in slug_dir.glob('*.jsonl') if mtime_utc(path) >= cutoff]
    if not paths:
        # Slug dir missing or empty: match by cwd across the store instead.
        paths = [
            path
            for path in SESSIONS_DIR.rglob('*.jsonl')
            if mtime_utc(path) >= cutoff and read_project_hint(path) == str(project_path)
        ]

    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths[:cap]


def read_project_hint(path: Path) -> str | None:
    """The cwd from the first `session` record, if the file opens."""
    try:
        with path.open(encoding='utf-8', errors='replace') as handle:
            first = handle.readline().strip()
    except OSError:
        return None
    if not first:
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    if isinstance(record, dict) and record.get('type') == 'session' and isinstance(record.get('cwd'), str):
        return record['cwd']
    return None


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return normalize_text(content)
    if not isinstance(content, list):
        return ''
    parts = [
        block['text']
        for block in content
        if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str)
    ]
    return normalize_text('\n'.join(parts))


def extract_turn(record: dict[str, Any]) -> Turn | None:
    if record.get('type') != 'message':
        return None
    message = record.get('message')
    if not isinstance(message, dict):
        return None
    role = message.get('role')
    if role not in {'user', 'assistant'}:
        return None
    text = _extract_message_text(message.get('content'))
    if not text:
        return None
    return Turn(role=role, text=text, timestamp=record.get('timestamp') or message.get('timestamp'))


def summarize(path: Path, keywords: list[str]) -> SessionSummary | None:
    turns: list[Turn] = []
    started_at: str | None = None
    for record in iter_jsonl(path):
        if started_at is None:
            started_at = record.get('timestamp')
        turn = extract_turn(record)
        if turn is not None:
            turns.append(turn)
    if not turns:
        return None
    project_hint = read_project_hint(path)
    return build_summary(
        'pi', path, turns, started_at, keywords,
        project_hint=project_hint,
        cwd=project_hint,
    )
