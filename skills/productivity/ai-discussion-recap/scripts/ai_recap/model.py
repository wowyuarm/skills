"""Shared data types, text helpers, scoring, and the tolerant JSONL reader."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

PREVIEW_LIMIT = 280
EDGE_PREVIEW_HEAD_RATIO = 0.6
DEDUPE_TEXT_PREFIX = 200
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
    cwd: str | None = None
    git_branch: str | None = None
    model: str | None = None
    keywords: tuple[str, ...] = field(default_factory=tuple)

    @property
    def preview(self) -> str:
        keywords_lower = tuple(k.lower() for k in self.keywords)
        if keywords_lower:
            for turn in self.turns:
                if turn.role == 'user' and turn.text and any(k in turn.text.lower() for k in keywords_lower):
                    return shorten(turn.text, PREVIEW_LIMIT)
        for turn in self.turns:
            if turn.role == 'user' and turn.text:
                return shorten(turn.text, PREVIEW_LIMIT)
        for turn in self.turns:
            if turn.text:
                return shorten(turn.text, PREVIEW_LIMIT)
        return ''


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


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


def dedupe_consecutive(turns: list[Turn]) -> list[Turn]:
    out: list[Turn] = []
    for turn in turns:
        if out and out[-1].role == turn.role and out[-1].text[:DEDUPE_TEXT_PREFIX] == turn.text[:DEDUPE_TEXT_PREFIX]:
            continue
        out.append(turn)
    return out


def build_summary(
    source: str,
    path: Path,
    turns: list[Turn],
    started_at: str | None,
    keywords: list[str],
    **metadata_fields: Any,
) -> SessionSummary | None:
    """Shared tail of every per-source summarizer: dedupe, score, stamp."""
    turns = dedupe_consecutive(turns)
    if not turns:
        return None
    return SessionSummary(
        source=source,
        path=path,
        modified_at=mtime_utc(path),
        started_at=started_at,
        turns=turns,
        score=score_session(turns, keywords),
        keywords=tuple(keywords),
        **metadata_fields,
    )


def mtime_utc(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def iter_jsonl(path: Path) -> Iterator[dict]:
    """Yield object records from a JSONL file, tolerating real-world damage:
    undecodable bytes are replaced instead of crashing the run, and lines that
    fail to parse or are not JSON objects are skipped."""
    with path.open(encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record
