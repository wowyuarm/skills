"""Markdown and JSON rendering of the candidate session list."""

from __future__ import annotations

import json
from pathlib import Path

from .model import SessionSummary, shorten

TURN_SAMPLE_LIMIT = 6
TURN_PREVIEW_LIMIT = 220


def to_markdown(project: Path, sessions: list[SessionSummary]) -> str:
    lines = [
        '# Discussion Candidates',
        '',
        f'- Project: `{project}`',
        f'- Sessions: {len(sessions)}',
        '',
    ]
    for index, session in enumerate(sessions, start=1):
        lines.append(f'## {index}. {session.path.name}')
        lines.append(f'- Source: {session.source}')
        lines.append(f'- Modified: {session.modified_at.isoformat()}')
        if session.started_at:
            lines.append(f'- Started: {session.started_at}')
        if session.cwd:
            lines.append(f'- Cwd: `{session.cwd}`')
        if session.git_branch:
            lines.append(f'- Git branch: `{session.git_branch}`')
        if session.model:
            lines.append(f'- Model: `{session.model}`')
        lines.append(f'- Score: {session.score}')
        lines.append(f'- Preview: {session.preview or "(no preview)"}')
        lines.append('- Turns:')
        for turn in session.turns[:TURN_SAMPLE_LIMIT]:
            lines.append(f'  - {turn.role}: {shorten(turn.text, TURN_PREVIEW_LIMIT)}')
        if len(session.turns) > TURN_SAMPLE_LIMIT:
            lines.append(f'  - ... {len(session.turns) - TURN_SAMPLE_LIMIT} more extracted turns')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def to_json(project: Path, sessions: list[SessionSummary]) -> str:
    payload = {
        'project': str(project),
        'sessions': [
            {
                'source': session.source,
                'path': str(session.path),
                'modified_at': session.modified_at.isoformat(),
                'started_at': session.started_at,
                'cwd': session.cwd,
                'git_branch': session.git_branch,
                'model': session.model,
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
