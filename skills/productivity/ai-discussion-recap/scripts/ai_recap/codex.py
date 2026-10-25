"""Codex store: ~/.codex/sessions/**/rollout-*.jsonl."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .model import Turn, build_summary, iter_jsonl, mtime_utc, normalize_text, SessionSummary

SESSIONS_DIR = Path.home() / '.codex' / 'sessions'
# Injected blocks start the message; anchoring at the start avoids dropping
# real turns that merely quote one of these phrases.
NOISE_PREFIXES = (
    '# AGENTS.md instructions for ',
    '<environment_context>',
    '<turn_aborted>',
    '## Reasoning',
    'Let me think about',
)


def load_paths(project_path: Path, *, days: int, cap: int) -> list[Path]:
    if not SESSIONS_DIR.exists():
        raise FileNotFoundError(f'Codex sessions directory not found: {SESSIONS_DIR}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    paths = [
        path
        for path in SESSIONS_DIR.rglob('rollout-*.jsonl')
        if mtime_utc(path) >= cutoff and read_project_hint(path) == str(project_path)
    ]
    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    # Cap before summarizing: parsing every rollout in the window would make
    # the scan O(store) instead of O(cap).
    return paths[:cap]


def read_project_hint(path: Path) -> str | None:
    """The cwd from the first `session_meta` record, if the file opens."""
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
    if isinstance(record, dict) and record.get('type') == 'session_meta':
        payload = record.get('payload')
        if isinstance(payload, dict) and isinstance(payload.get('cwd'), str):
            return payload['cwd']
    return None


def _extract_message_text(content: Any) -> str:
    if not isinstance(content, list):
        return ''
    parts = [
        block['text']
        for block in content
        if isinstance(block, dict) and block.get('type') in {'input_text', 'output_text'} and isinstance(block.get('text'), str)
    ]
    text = normalize_text('\n'.join(parts))
    if text and any(text.startswith(prefix) for prefix in NOISE_PREFIXES):
        return ''
    return text


def extract_turn(record: dict[str, Any]) -> Turn | None:
    if record.get('type') != 'response_item':
        return None
    payload = record.get('payload')
    if not isinstance(payload, dict) or payload.get('type') != 'message':
        return None
    role = payload.get('role')
    if role not in {'user', 'assistant'}:
        return None
    text = _extract_message_text(payload.get('content'))
    if not text:
        return None
    return Turn(role=role, text=text, timestamp=record.get('timestamp'))


def read_metadata(path: Path) -> dict[str, str]:
    """Model from the session_meta record (the first line of a rollout)."""
    first = next(iter_jsonl(path), None)
    if not first or first.get('type') != 'session_meta' or not isinstance(first.get('payload'), dict):
        return {}
    payload = first['payload']
    for key in ('model', 'model_provider'):
        if isinstance(payload.get(key), str):
            return {'model': payload[key]}
    return {}


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
        'codex', path, turns, started_at, keywords,
        project_hint=project_hint,
        cwd=project_hint,
        model=read_metadata(path).get('model'),
    )
