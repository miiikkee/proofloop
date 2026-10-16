from pathlib import Path

import pytest

from agent.safety import ALLOWED_FILES, PatchRejected, apply_patch, validate_patch
from agent.schemas import PatchProposal

ROOT = Path(__file__).resolve().parent.parent
CONTACT = "fixture_site/templates/contact.html"
SRC = (ROOT / CONTACT).read_text()


def P(**kw):
    base = dict(root_cause="x", file_path=CONTACT, find_text='id="send" type="button"',
                replace_text='id="send" type="submit"', reason="r", confidence=0.9)
    base.update(kw)
    return PatchProposal(**base)


def test_valid_patch_applies_once():
    out = apply_patch(P(), SRC)
    assert 'type="submit"' in out and out.count("\n") == SRC.count("\n")


@pytest.mark.parametrize("path", ["fixture_site/app.py", ".env", "../etc/passwd", "agent/safety.py",
                                  "tests/acceptance.py", "fixture_site/templates/../app.py"])
def test_rejects_files_outside_allowlist(path):
    with pytest.raises(PatchRejected):
        validate_patch(P(file_path=path), SRC)


def test_rejects_ambiguous_find_text():
    with pytest.raises(PatchRejected, match="exactly once"):
        validate_patch(P(find_text="<label"), SRC)


def test_rejects_missing_find_text():
    with pytest.raises(PatchRejected, match="found 0"):
        validate_patch(P(find_text="not in file"), SRC)


def test_rejects_oversized_edit():
    with pytest.raises(PatchRejected, match="exceeds"):
        validate_patch(P(replace_text="x" * 1000), SRC)


@pytest.mark.parametrize("bad", ['type="submit"><script>alert(1)</script>',
                                 'type="submit" onclick="fetch(1)"',
                                 'type="submit" formaction="https://evil.example"'])
def test_rejects_script_or_external_markup(bad):
    with pytest.raises(PatchRejected):
        validate_patch(P(replace_text='id="send" ' + bad), SRC)


def test_rejects_credentials():
    with pytest.raises(PatchRejected, match="credential"):
        validate_patch(P(replace_text='id="send" data-x="api_key=abc"'), SRC)


def test_allowlist_is_templates_only():
    assert all(p.startswith("fixture_site/templates/") for p in ALLOWED_FILES)


def test_reference_fixture_still_broken():
    # The reference copy must keep the intentional defect; repairs live only in the sandbox.
    assert 'id="send" type="button"' in SRC
