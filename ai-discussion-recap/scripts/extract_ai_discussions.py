#!/usr/bin/env python3
"""Extract high-signal Claude Code, Codex, or Pi discussion turns from local session logs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

CLAUDE_PROJECTS_DIR = Path.home() / '.claude' / 'projects'
CODEX_SESSIONS_DIR = Path.home() / '.codex' / 'sessions'
PI_SESSIONS_DIR = Path.home() / '.pi' / 'agent' / 'sessions'
DEFAULT_DAYS = 14
DEFAULT_MAX_SESSIONS = 8
PREVIEW_LIMIT = 280
EDGE_PREVIEW_HEAD_RATIO = 0.6
LOW_SIGNAL_USER_MESSAGES = {
    'continue',
    'ok',
    'okay',
    'thanks',
    'thx',
    'go on',
    'run tests',
    '继续',
    '好的',
}
CODEX_NOISE_PATTERNS = (
    '# AGENTS.md instructions for ',
    '<environment_context>',
    '<turn_aborted>',
)
KEYWORD_BONUS = {
    'principle',
    'principles',
    'design',
    'architecture',
    'refactor',
    'plan',
    'worker',
    'memory',
    'brief',
    'thread',
    'session',
    'decision',
    'tradeoff',
    '总结',
    '原则',
    '架构',
    '设计',
    '重构',
    '计划',
    '讨论',
}


@dataclass(slots=True)
class Turn:
    role: str
    text: str
    timestamp: str | None


@dataclass(slots=True)
class SessionSummary:
    source: str
    path: Path
    modified_at: datetime
    started_at: str | None
    turns: list[Turn]
    score: int
    project_hint: str | None = None

    @property
    def preview(self) -> str:
        for turn in self.turns:
            if turn.role == 'user' and turn.text:
                return shorten(turn.text, PREVIEW_LIMIT)
        for turn in self.turns:
            if turn.text:
                return shorten(turn.text, PREVIEW_LIMIT)
        return ''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Absolute project path, for example /home/yu/projects/HaL')
    parser.add_argument('--project-slug', help='Explicit Claude project slug under ~/.claude/projects/')
    parser.add_argument(
        '--source',
        choices=['all', 'claude', 'codex', 'pi'],
        default='all',
        help='Choose which conversation store to inspect',
    )
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS)
    parser.add_argument('--max-sessions', type=int, default=DEFAULT_MAX_SESSIONS)
    parser.add_argument('--keyword', action='append', default=[])
    parser.add_argument('--json', action='store_true', help='Emit JSON instead of markdown')
    return parser.parse_args()


def shorten(text: str, limit: int) -> str:
    compact = re.sub(r'\s+', ' ', text).strip()
    if len(compact) <= limit:
        return compact
    if limit < 40:
        return compact[: limit - 3].rstrip() + '...'
    head = int(limit * EDGE_PREVIEW_HEAD_RATIO)
    tail = limit - head - 7
    if tail < 12:
        tail = 12
        head = max(limit - tail - 7, 12)
    return f'{compact[:head].rstrip()} ... {compact[-tail:].lstrip()}'


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def derive_project_slug(project_path: str) -> str:
    value = project_path.strip()
    if not value:
        raise ValueError('--project cannot be empty')
    return value.replace('/', '-')


def derive_pi_project_slug(project_path: Path) -> str:
    value = str(project_path).strip()
    if not value:
        raise ValueError('--project cannot be empty')
    slug = value.strip('/').replace('/', '-')
    return f'--{slug}--'


def resolve_project_dir(args: argparse.Namespace) -> Path:
    if args.project_slug:
        return CLAUDE_PROJECTS_DIR / args.project_slug
    if args.project:
        return CLAUDE_PROJECTS_DIR / derive_project_slug(args.project)
    return CLAUDE_PROJECTS_DIR / derive_project_slug(str(Path.cwd()))


def resolve_project_path(args: argparse.Namespace) -> Path:
    if args.project:
        return Path(args.project).expanduser().resolve()
    return Path.cwd().resolve()


def load_recent_claude_session_paths(project_dir: Path, *, days: int, max_sessions: int) -> list[Path]:
    if not project_dir.exists():
        raise FileNotFoundError(f'Claude project directory not found: {project_dir}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    paths: list[Path] = []
    for path in project_dir.glob('*.jsonl'):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if modified >= cutoff:
            paths.append(path)
    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths[:max_sessions]


def load_recent_codex_session_paths(project_path: Path, *, days: int) -> list[Path]:
    if not CODEX_SESSIONS_DIR.exists():
        raise FileNotFoundError(f'Codex sessions directory not found: {CODEX_SESSIONS_DIR}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    paths: list[Path] = []
    for path in CODEX_SESSIONS_DIR.rglob('rollout-*.jsonl'):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if modified < cutoff:
            continue
        session_project = read_codex_session_project_hint(path)
        if session_project == str(project_path):
            paths.append(path)
    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths


def load_recent_pi_session_paths(project_path: Path, *, days: int) -> list[Path]:
    if not PI_SESSIONS_DIR.exists():
        raise FileNotFoundError(f'Pi sessions directory not found: {PI_SESSIONS_DIR}')
    cutoff = datetime.now(UTC) - timedelta(days=days)
    project_slug = derive_pi_project_slug(project_path)
    candidate_dirs = [PI_SESSIONS_DIR / project_slug]
    paths: list[Path] = []

    for session_dir in candidate_dirs:
        if not session_dir.exists():
            continue
        for path in session_dir.glob('*.jsonl'):
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified >= cutoff:
                paths.append(path)

    if not paths:
        for path in PI_SESSIONS_DIR.rglob('*.jsonl'):
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified < cutoff:
                continue
            session_project = read_pi_session_project_hint(path)
            if session_project == str(project_path):
                paths.append(path)

    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths


def extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return normalize_text(content)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get('type')
            if block_type == 'text' and isinstance(block.get('text'), str):
                parts.append(block['text'])
            elif block_type == 'tool_result':
                continue
        return normalize_text('\n'.join(parts))
    return ''


def extract_turn(record: dict[str, Any]) -> Turn | None:
    record_type = record.get('type')
    timestamp = record.get('timestamp') or record.get('ts')

    if record_type in {'user', 'assistant'}:
        message = record.get('message')
        if isinstance(message, dict):
            text = extract_text_from_content(message.get('content'))
            if text:
                return Turn(role=record_type, text=text, timestamp=timestamp)
        return None

    if record_type == 'user_message':
        payload = record.get('payload')
        if isinstance(payload, dict) and isinstance(payload.get('content'), str):
            text = normalize_text(payload['content'])
            if text:
                return Turn(role='user', text=text, timestamp=timestamp)
    return None


def extract_codex_message_text(content: Any) -> str:
    if not isinstance(content, list):
        return ''
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        block_type = block.get('type')
        if block_type in {'input_text', 'output_text'} and isinstance(block.get('text'), str):
            parts.append(block['text'])
    return normalize_text('\n'.join(parts))


def extract_pi_message_text(content: Any) -> str:
    if isinstance(content, str):
        return normalize_text(content)
    if not isinstance(content, list):
        return ''
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get('type') == 'text' and isinstance(block.get('text'), str):
            parts.append(block['text'])
    return normalize_text('\n'.join(parts))


def extract_codex_turn(record: dict[str, Any]) -> Turn | None:
    if record.get('type') != 'response_item':
        return None
    payload = record.get('payload')
    if not isinstance(payload, dict):
        return None
    if payload.get('type') != 'message':
        return None
    role = payload.get('role')
    if role not in {'user', 'assistant'}:
        return None
    text = extract_codex_message_text(payload.get('content'))
    if not text:
        return None
    if role == 'user' and any(pattern in text for pattern in CODEX_NOISE_PATTERNS):
        return None
    return Turn(role=role, text=text, timestamp=record.get('timestamp'))


def extract_pi_turn(record: dict[str, Any]) -> Turn | None:
    if record.get('type') != 'message':
        return None
    message = record.get('message')
    if not isinstance(message, dict):
        return None
    role = message.get('role')
    if role not in {'user', 'assistant'}:
        return None
    text = extract_pi_message_text(message.get('content'))
    if not text:
        return None
    return Turn(role=role, text=text, timestamp=record.get('timestamp') or message.get('timestamp'))


def read_codex_session_project_hint(path: Path) -> str | None:
    try:
        with path.open(encoding='utf-8') as handle:
            first = handle.readline().strip()
    except OSError:
        return None
    if not first:
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    if record.get('type') != 'session_meta':
        return None
    payload = record.get('payload')
    if isinstance(payload, dict):
        cwd = payload.get('cwd')
        if isinstance(cwd, str):
            return cwd
    return None


def read_pi_session_project_hint(path: Path) -> str | None:
    try:
        with path.open(encoding='utf-8') as handle:
            first = handle.readline().strip()
    except OSError:
        return None
    if not first:
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    if record.get('type') != 'session':
        return None
    cwd = record.get('cwd')
    if isinstance(cwd, str):
        return cwd
    return None


def score_session(turns: list[Turn], keywords: list[str]) -> int:
    if not turns:
        return 0
    score = 0
    first_user = next((turn.text for turn in turns if turn.role == 'user' and turn.text), '')
    first_user_lower = first_user.lower()

    if first_user:
        score += min(len(first_user) // 80, 6)
        if first_user_lower in LOW_SIGNAL_USER_MESSAGES:
            score -= 4
    for keyword in KEYWORD_BONUS.union({value.lower() for value in keywords}):
        if keyword and keyword in first_user_lower:
            score += 2
    assistant_long_turns = sum(1 for turn in turns if turn.role == 'assistant' and len(turn.text) >= 400)
    score += min(assistant_long_turns, 4)
    score += min(len(turns), 12)
    return score


def summarize_session(path: Path, keywords: list[str]) -> SessionSummary | None:
    turns: list[Turn] = []
    started_at: str | None = None
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if started_at is None:
                started_at = record.get('timestamp') or record.get('ts')
            turn = extract_turn(record)
            if turn is not None:
                turns.append(turn)
    if not turns:
        return None
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionSummary(
        source='claude',
        path=path,
        modified_at=modified_at,
        started_at=started_at,
        turns=turns,
        score=score_session(turns, keywords),
    )


def summarize_codex_session(path: Path, keywords: list[str]) -> SessionSummary | None:
    turns: list[Turn] = []
    started_at: str | None = None
    project_hint = read_codex_session_project_hint(path)
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if started_at is None:
                started_at = record.get('timestamp')
            turn = extract_codex_turn(record)
            if turn is not None:
                turns.append(turn)
    if not turns:
        return None
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionSummary(
        source='codex',
        path=path,
        modified_at=modified_at,
        started_at=started_at,
        turns=turns,
        score=score_session(turns, keywords),
        project_hint=project_hint,
    )


def summarize_pi_session(path: Path, keywords: list[str]) -> SessionSummary | None:
    turns: list[Turn] = []
    started_at: str | None = None
    project_hint = read_pi_session_project_hint(path)
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if started_at is None:
                started_at = record.get('timestamp')
            turn = extract_pi_turn(record)
            if turn is not None:
                turns.append(turn)
    if not turns:
        return None
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionSummary(
        source='pi',
        path=path,
        modified_at=modified_at,
        started_at=started_at,
        turns=turns,
        score=score_session(turns, keywords),
        project_hint=project_hint,
    )


def to_markdown(project_dir: Path, sessions: list[SessionSummary]) -> str:
    lines = [
        '# Discussion Candidates',
        '',
        f'- Project: `{project_dir}`',
        f'- Sessions: {len(sessions)}',
        '',
    ]
    for index, session in enumerate(sessions, start=1):
        lines.append(f'## {index}. {session.path.name}')
        lines.append(f'- Source: {session.source}')
        lines.append(f'- Modified: {session.modified_at.isoformat()}')
        if session.started_at:
            lines.append(f'- Started: {session.started_at}')
        if session.project_hint:
            lines.append(f'- Session cwd: `{session.project_hint}`')
        lines.append(f'- Score: {session.score}')
        lines.append(f'- Preview: {session.preview or "(no preview)"}')
        lines.append('- Turns:')
        for turn in session.turns[:6]:
            lines.append(f'  - {turn.role}: {shorten(turn.text, 220)}')
        if len(session.turns) > 6:
            lines.append(f'  - ... {len(session.turns) - 6} more extracted turns')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def to_json(project_dir: Path, sessions: list[SessionSummary]) -> str:
    payload = {
        'project': str(project_dir),
        'sessions': [
            {
                'source': session.source,
                'path': str(session.path),
                'modified_at': session.modified_at.isoformat(),
                'started_at': session.started_at,
                'project_hint': session.project_hint,
                'score': session.score,
                'preview': session.preview,
                'turns': [
                    {
                        'role': turn.role,
                        'timestamp': turn.timestamp,
                        'text': turn.text,
                    }
                    for turn in session.turns
                ],
            }
            for session in sessions
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    project_path = resolve_project_path(args)
    sessions = []
    if args.source in {'all', 'claude'}:
        project_dir = resolve_project_dir(args)
        try:
            claude_paths = load_recent_claude_session_paths(
                project_dir,
                days=args.days,
                max_sessions=args.max_sessions,
            )
        except FileNotFoundError:
            if args.source == 'claude':
                raise
            claude_paths = []
        for path in claude_paths:
            summary = summarize_session(path, args.keyword)
            if summary is not None:
                sessions.append(summary)
    if args.source in {'all', 'codex'}:
        try:
            codex_paths = load_recent_codex_session_paths(project_path, days=args.days)
        except FileNotFoundError:
            if args.source == 'codex':
                raise
            codex_paths = []
        for path in codex_paths:
            summary = summarize_codex_session(path, args.keyword)
            if summary is not None:
                sessions.append(summary)
    if args.source in {'all', 'pi'}:
        try:
            pi_paths = load_recent_pi_session_paths(project_path, days=args.days)
        except FileNotFoundError:
            if args.source == 'pi':
                raise
            pi_paths = []
        for path in pi_paths:
            summary = summarize_pi_session(path, args.keyword)
            if summary is not None:
                sessions.append(summary)
    sessions.sort(key=lambda item: (item.score, item.modified_at), reverse=True)
    sessions = sessions[: args.max_sessions]
    if args.json:
        print(to_json(project_path, sessions))
    else:
        print(to_markdown(project_path, sessions), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
