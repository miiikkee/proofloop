"""Bug-injection scenarios for the test suite.

Each scenario derives the site served in the sandbox from the reference fixture by
exact-text mutations. Only the orchestrator's staging step reads this file; the
diagnosing LLM sees the resulting site files, never these definitions.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTACT = "fixture_site/templates/contact.html"
INDEX = "fixture_site/templates/index.html"

# The reference fixture ships with the contact-button bug. Other scenarios repair
# that first, then inject a different single defect.
_FIX_BUTTON = (CONTACT, '<button id="send" type="button">', '<button id="send" type="submit">')

SCENARIOS: dict[str, dict] = {
    "contact-button": {
        "description": "Send button is type=button, so the form never submits",
        "mutations": [],
    },
    "broken-nav-link": {
        "description": "Homepage 'Contact us' link points to a route that does not exist",
        "mutations": [_FIX_BUTTON, (INDEX, 'href="/contact"', 'href="/contact-us"')],
    },
    "wrong-form-action": {
        "description": "Contact form posts to a route that does not exist",
        "mutations": [_FIX_BUTTON, (CONTACT, 'action="/contact"', 'action="/send-message"')],
    },
}
DEFAULT = "contact-button"


def build_files(name: str, files: list[str]) -> dict[str, str]:
    """Return {repo-relative path: text} for the site under the given scenario."""
    out = {rel: (ROOT / rel).read_text() for rel in files}
    for rel, find, repl in SCENARIOS[name]["mutations"]:
        assert out[rel].count(find) == 1, f"scenario {name}: mutation anchor not unique in {rel}"
        out[rel] = out[rel].replace(find, repl, 1)
    return out
