# ProofLoop

**The AI agent that doesn't just find bugs. It proves they're fixed.**

ProofLoop reproduces a broken user journey in a real cloud browser, reads the allowlisted source, asks an LLM for a bounded patch, applies it only to an isolated candidate copy inside a Daytona sandbox, and then re-runs the same browser checks independently. Final pass/fail comes from the browser, not from the model's confidence.

> Scope: this is a hackathon prototype run against **one controlled, intentionally broken demo site** (`fixture_site/`). It is not production ready.

## How it works

```
CLI (python app.py)
  │
  ├─ Daytona sandbox ── baseline copy  (:3000) ── signed preview URL ─┐
  │                  └─ candidate copy (:3001)  ── signed preview URL ─┤
  │                                                                    │
  ├─ Anchor Browser (cloud Chromium over CDP) ◄────────────────────────┘
  │     3 fixed acceptance checks + screenshot
  │
  ├─ LLM diagnose → JSON {root_cause, file_path, find_text, replace_text, reason, confidence}
  ├─ Safety gate  → exact file allowlist, find_text occurs exactly once, size cap,
  │                 no scripts / handlers / external URLs / credentials
  ├─ Patch candidate copy only → fixed sandbox checks (py_compile, Flask routes)
  ├─ Anchor re-verifies candidate preview
  ├─ Arize AX traces: provision · detect · diagnose · patch · test · verify
  └─ artifacts/run_report.json, patch.diff, baseline.png, candidate.png, before_after.png
```

| Step | Tool | What happens |
|---|---|---|
| Provision | **Daytona** Python SDK | One ephemeral sandbox, two separate copies of the site, each served on its own port behind an expiring signed preview URL (1h) |
| Detect | **Anchor Browser** + Playwright over CDP | Cloud browser runs 3 acceptance checks against the baseline preview |
| Diagnose | LLM (Anthropic or OpenAI) | Gets failing-check evidence + allowlisted template source + read-only backend; page text is treated as untrusted data |
| Patch | `agent/safety.py` | Proposal is validated, then written to the **candidate** copy only |
| Test | Daytona `process.exec` | Developer-defined commands only (no model-generated shell) |
| Verify | **Anchor Browser** | Same 3 checks, fresh session, against the candidate preview |
| Observe | **Arize AX** (OpenTelemetry / OpenInference) | Span per step with pass counts, root cause, confidence |

## The demo bug

`fixture_site/templates/contact.html` ships with `<button id="send" type="button">`. The backend `POST /contact` works, but clicking **Send message** never submits the form. Nothing in the orchestrator knows this answer; the LLM has to infer it from the browser evidence and the source.

Acceptance checks (`tests/acceptance.py`, fixed by the developer):
1. `homepage_heading`: homepage shows the "Acme Studio" heading
2. `contact_page_reachable`: clicking "Contact us" opens the form
3. `contact_submit_thank_you`: filling the form and clicking Send shows "Thank you"

## Results

<!-- RESULTS -->

## Safety controls

- Patch may touch only `fixture_site/templates/{index,contact,success}.html` (exact allowlist).
- `find_text` must occur exactly once; edits capped at 300 chars; scripts, event handlers, external URLs and credential-like strings are rejected.
- Maximum 2 patch attempts. A failed attempt resets the candidate to baseline before retrying.
- The model never produces shell commands; the sandbox only runs fixed commands from `agent/repair.py`.
- Baseline and candidate are separate copies; the run report records `baseline_copy_modified` (checked after every run).
- Preview URLs are signed and expire; tokens are redacted from logs and the report. The sandbox is deleted after the run.
- No auto-merge, no push, no deploy: a verified patch ends in status `verified_awaiting_human_approval`.
- `tests/test_safety.py`: 16 unit tests for the gate.

## Run it

```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env    # fill DAYTONA_API_KEY, ANCHOR_API_KEY, one LLM key, optional ARIZE_*
python -m pytest -q tests/test_safety.py
python app.py           # full loop; add --keep-sandbox to keep previews up for a live demo
```

Local-only fixture check (no keys needed):

```bash
PORT=3000 python fixture_site/app.py &
python -m tests.acceptance http://127.0.0.1:3000   # expect 2/3
```

Without `ANCHOR_API_KEY` the browser step falls back to local Playwright, and the report's `browser_provider` says so.

## Limitations

- One controlled bug on one demo site; pass counts are test-case results, not accuracy claims.
- Text-only evidence to the LLM (screenshot is saved but not sent to the model).
- Single-file, find/replace edits only.

## Next steps

CI integration (run on every preview deploy), multi-file patches with review UI, SurrealDB memory of verified fixes so repeat bugs are recognized faster.
