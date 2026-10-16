"""Patch validation gates. Independent of the LLM that proposes the patch."""
from __future__ import annotations

import re

from agent.schemas import PatchProposal

# Exact allowlist: the only files a patch may touch.
ALLOWED_FILES = frozenset({
    "fixture_site/templates/index.html",
    "fixture_site/templates/contact.html",
    "fixture_site/templates/success.html",
})
MAX_EDIT_CHARS = 300
MAX_ATTEMPTS = 2

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]"),
    re.compile(r"\b(sk-[A-Za-z0-9]{10,}|dtn_[A-Za-z0-9]{10,}|gh[pousr]_[A-Za-z0-9]{10,}|AKIA[A-Z0-9]{12,}|ASIA[A-Z0-9]{12,})"),
]
_FORBIDDEN_MARKUP = re.compile(r"(?i)<\s*script|javascript:|on\w+\s*=|<\s*iframe|https?://")


class PatchRejected(ValueError):
    pass


def validate_patch(p: PatchProposal, source: str) -> None:
    """Raise PatchRejected unless the patch is small, exact, and allowlisted."""
    if p.file_path not in ALLOWED_FILES:
        raise PatchRejected(f"file not on allowlist: {p.file_path!r}")
    if not p.find_text:
        raise PatchRejected("find_text is empty")
    if p.find_text == p.replace_text:
        raise PatchRejected("replace_text is identical to find_text")
    if len(p.find_text) > MAX_EDIT_CHARS or len(p.replace_text) > MAX_EDIT_CHARS:
        raise PatchRejected(f"edit exceeds {MAX_EDIT_CHARS} chars")
    count = source.count(p.find_text)
    if count != 1:
        raise PatchRejected(f"find_text must occur exactly once, found {count}")
    for pat in _SECRET_PATTERNS:
        if pat.search(p.replace_text):
            raise PatchRejected("replace_text looks like it contains a credential")
    # New markup may not introduce scripts, event handlers, or external URLs.
    if _FORBIDDEN_MARKUP.search(p.replace_text) and not _FORBIDDEN_MARKUP.search(p.find_text):
        raise PatchRejected("replace_text introduces scripts, handlers, or external URLs")
    if not 0.0 <= p.confidence <= 1.0:
        raise PatchRejected("confidence out of range")


def apply_patch(p: PatchProposal, source: str) -> str:
    validate_patch(p, source)
    return source.replace(p.find_text, p.replace_text, 1)
