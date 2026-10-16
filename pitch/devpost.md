# ProofLoop: Devpost submission text

## Elevator pitch (one line)
The AI agent that doesn't just find bugs. It proves they're fixed.

## Summary
ProofLoop is an autonomous website QA and safe-repair agent. It reproduces a broken user journey in a real cloud browser (Anchor Browser), asks Claude to propose a bounded source patch, applies that patch only to an isolated candidate copy inside a Daytona sandbox, and re-runs the same browser checks independently. A fix counts as fixed only when the browser says so, not when the model says so.

## The problem
Teams find broken web flows after customers complain. AI coding agents can propose fixes, but "the model is confident" is not evidence. Engineers still need to reproduce the bug, try the fix somewhere safe, and prove the user journey works again.

## What it does
1. **Provision**: the Daytona Python SDK creates an ephemeral sandbox holding two separate copies of the site (baseline and candidate). Each copy is served behind an expiring signed preview URL.
2. **Detect**: an Anchor Browser cloud session (Playwright over CDP) runs 3 fixed acceptance checks against the baseline. Result: 2/3. Clicking "Send message" on the contact form never shows "Thank you".
3. **Diagnose**: Claude Sonnet 5.5 on Amazon Bedrock receives the failing-check evidence plus the allowlisted template source. It returns structured JSON: `{root_cause, file_path, find_text, replace_text, reason, confidence}`. The answer is not hardcoded anywhere.
4. **Gate and patch**: a deterministic safety gate enforces an exact file allowlist, requires `find_text` to occur exactly once, caps the edit size, and blocks scripts, event handlers, external URLs and credential-like strings. The patch goes to the candidate copy only.
5. **Test**: Daytona runs developer-defined checks (py_compile, Flask route tests). Model-generated shell commands are never executed.
6. **Verify**: a fresh Anchor session runs the same 3 checks against the candidate preview. Result: 3/3.
7. **Report**: run_report.json, patch diff, before/after screenshots and per-step timings. Each step is traced to Arize AX via OpenTelemetry/OpenInference, and the traces were confirmed in the Arize UI (project `proofloop`).

## Measured results (3 consecutive real runs)
| Run | Baseline | Candidate | Attempts | Runtime |
|---|---|---|---|---|
| 1 | 2/3 | 3/3 | 1 | 34.2 s |
| 2 | 2/3 | 3/3 | 1 | 41.9 s |
| 3 | 2/3 | 3/3 | 1 | 38.6 s |

These are 3 test cases on one controlled demo site, not an accuracy benchmark.

## Sponsor tools and how we used them
- **Daytona**: ephemeral sandbox, two isolated copies (baseline and candidate), fixed-command execution, signed and expiring preview URLs that make the sandboxed sites reachable by a cloud browser, and automatic deletion after the run.
- **Anchor Browser**: the cloud Chromium that reproduces the failure and independently verifies the fix. A cloud browser cannot reach laptop localhost, so Daytona previews and Anchor are paired by design.
- **Arize AX**: OpenTelemetry/OpenInference spans for provision, detect, diagnose, patch, test and verify. Each span carries pass counts, root cause and confidence.
- **AWS (Amazon Bedrock)**: Claude Sonnet 5.5 via the Bedrock Converse API, running under the event lab account.

## Safety
Exact file allowlist · find_text must match exactly once · 300-character edit cap · no scripts, handlers, external URLs or secrets · maximum 2 attempts · no model-generated shell commands · the baseline copy is never modified (checked on every run) · preview tokens are redacted from logs · no auto-merge, push or deploy: a verified patch waits for human approval · 16 unit tests for the safety gate.

## Limitations (disclosed)
One intentionally broken demo site with one controlled bug (a contact form button with `type="button"`). Single-file find/replace patches only. Screenshots are saved as evidence but not sent to the model.

## What's next
Run on every preview deploy in CI, support multi-file patches with a review UI, and use SurrealDB agent memory to recall verified fixes for repeat bugs.

## Links
- Source: https://github.com/miiikkee/proofloop
