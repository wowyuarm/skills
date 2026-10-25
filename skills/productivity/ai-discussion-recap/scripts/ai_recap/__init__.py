"""ai_recap: per-source extractors for local AI session log stores.

Each source module (claude, codex, pi) exposes the same two-call surface:
`load_paths(...)` discovering recent candidate files for a project, and
`summarize(path, keywords)` turning one file into a SessionSummary.
"""

from __future__ import annotations

from . import claude, codex, pi

SOURCES = {
    'claude': claude,
    'codex': codex,
    'pi': pi,
}
