#!/usr/bin/env python3
"""List high-signal discussion candidates from local Claude Code, Codex, and Pi
session logs: recent sessions whose cwd matches the target project, ranked by a
discussion-quality score, with previews and the first extracted turns.

Extraction lives in the ai_recap package next to this file; this is only the
command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_recap import SOURCES, claude
from ai_recap.model import SessionSummary
from ai_recap.render import to_json, to_markdown

DEFAULT_DAYS = 14
DEFAULT_MAX_SESSIONS = 8
DEFAULT_PER_SOURCE = 8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Absolute project path (default: current directory)')
    parser.add_argument('--project-slug', help='Explicit Claude project slug under ~/.claude/projects/, '
                                               'overriding the slug derived from --project')
    parser.add_argument('--source', choices=['all', 'claude', 'codex', 'pi'], default='all',
                        help='Which conversation store to inspect')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS)
    parser.add_argument('--max-sessions', type=int, default=DEFAULT_MAX_SESSIONS)
    parser.add_argument('--per-source', type=int, default=DEFAULT_PER_SOURCE,
                        help='Maximum sessions taken from each source before global ranking')
    parser.add_argument('--keyword', action='append', default=[],
                        help='Keyword that boosts a session in scoring; repeatable')
    parser.add_argument('--json', action='store_true',
                        help='Emit JSON instead of markdown (turns carry full text — large)')
    return parser.parse_args(argv)


def load_paths(source: str, args: argparse.Namespace, project_path: Path) -> list[Path]:
    if source == 'claude':
        slug = args.project_slug or claude.derive_project_slug(project_path)
        return SOURCES[source].load_paths(claude.PROJECTS_DIR / slug, project_path,
                                          days=args.days, cap=args.per_source)
    return SOURCES[source].load_paths(project_path, days=args.days, cap=args.per_source)


def collect(args: argparse.Namespace, project_path: Path) -> dict[str, list[SessionSummary]]:
    selected = list(SOURCES) if args.source == 'all' else [args.source]
    buckets: dict[str, list[SessionSummary]] = {}
    for name in selected:
        try:
            paths = load_paths(name, args, project_path)
        except FileNotFoundError as error:
            if args.source == name:
                sys.exit(f'error: {error}')
            print(f'note: {error}; skipping', file=sys.stderr)
            continue
        buckets[name] = [
            summary
            for summary in (SOURCES[name].summarize(path, args.keyword) for path in paths)
            if summary is not None
        ]
    return buckets


def rank(buckets: dict[str, list[SessionSummary]], per_source: int, max_sessions: int) -> list[SessionSummary]:
    sessions: list[SessionSummary] = []
    for bucket in buckets.values():
        bucket.sort(key=lambda item: (item.score, item.modified_at), reverse=True)
        sessions.extend(bucket[:per_source])
    sessions.sort(key=lambda item: (item.score, item.modified_at), reverse=True)
    return sessions[:max_sessions]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_path = Path(args.project).expanduser().resolve() if args.project else Path.cwd().resolve()
    sessions = rank(collect(args, project_path), args.per_source, args.max_sessions)
    if args.json:
        print(to_json(project_path, sessions))
    else:
        print(to_markdown(project_path, sessions), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
