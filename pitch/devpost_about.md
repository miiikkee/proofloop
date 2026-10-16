## Inspiration
Evaluation is the real bottleneck in AI work. AI agents can already propose code fixes, but "the model is confident" is not evidence. We wanted an agent whose fixes a team could trust when nobody is watching: a fix gets accepted only on independent evidence.

## What it does
ProofLoop reproduces a broken user journey in a real cloud browser, asks Claude for a bounded patch, applies it only to an isolated candidate copy, and accepts it only when the same independent browser checks pass.

1. **Provision (Daytona):** an ephemeral sandbox holds two separate copies of the site, baseline and candidate, each behind an expiring signed preview URL.
2. **Detect (Anchor Browser):** cloud Chromium runs 3 developer-written acceptance checks on the baseline. Result: **2/3**, because the contact form never submits.
3. **Recall (SurrealDB Agent Memory):** earlier verified or failed fixes for similar symptoms are recalled as untrusted hints, each traceable to its run id.
4. **Diagnose (Claude Sonnet 5.5 on AWS Bedrock):** returns structured JSON with `root_cause`, `file_path`, `find_text`, `replace_text`, `reason` and `confidence`. The fix is not hardcoded anywhere.
5. **Safety gate (deterministic code, outside the LLM):** exact file allowlist, `find_text` must occur exactly once, at most 300 characters, and no scripts, handlers, external URLs or secrets.
6. **Patch and test (Daytona):** the patch is written to the candidate copy only. Only fixed, developer-defined commands run; model-generated shell commands are never executed.
7. **Verify (Anchor Browser):** a fresh session runs the same 3 checks on the candidate. Result: **3/3**.
8. **Remember and report:** the outcome is stored in SurrealDB. A verified fix supersedes earlier failed attempts; a failed edit is stored as "do not repeat". The run produces a report, diff and before/after screenshots, and the patch waits for **human approval**: no auto-merge, no deploy.

**Arize AX** traces every step with OpenTelemetry/OpenInference, including Daytona SDK calls, Bedrock token counts and pass counts.

## Results (real runs, Oct 16 2026)
| Injected bug | Before | After | Attempts | Runtime |
|---|---|---|---|---|
| Send button is `type="button"` | 2/3 | **3/3** | 1 | 34.0 s |
| Nav link points to `/contact-us` (404) | 2/3 | **3/3** | 1 | 34.1 s |
| Form posts to `/send-message` (404) | 2/3 | **3/3** | 1 | 29.0 s |

The baseline copy was unmodified in every run. When the same bug was run again, SurrealDB recalled the earlier verified fix as the top hit, traceable to its run id. On a different bug, Claude explicitly ignored a memory hint that did not match. These are 3 checks × 3 scenarios on one controlled demo site, not an accuracy benchmark.

## How we built it
Python orchestrator (a finite-state machine with a maximum of 2 attempts), Flask demo site, Daytona Python SDK (sandbox, file system, process execution, signed previews), Anchor Browser over Playwright CDP, Claude via the Bedrock Converse API, Arize AX via `arize-otel` plus OpenInference instrumentors, and SurrealDB Agent Memory (`surrealdb[memory]`). The safety gate has 16 unit tests.

## Challenges we ran into
- A cloud browser can't reach laptop localhost, so the sites had to be served from the Daytona sandbox through signed preview URLs.
- Keeping preview access tokens out of logs, reports and traces.
- Flask template caching: each retry serves the candidate on a fresh port so the browser never sees a stale template.
- Making memory helpful without letting it become an authority: hints are labeled as untrusted, and the safety gate and the browser still decide.

## Accomplishments that we're proud of
- An end-to-end loop on all 5 sponsor tools, run for real rather than mocked.
- 3 different bugs, all fixed and independently verified on the first attempt.
- The model never grades its own work, and the original copy is never touched.

## What we learned
The hard part isn't generating a fix, it's deciding when to accept one. Separating the proposer (the LLM) from the judge (fixed browser checks plus deterministic gates) made the system much easier to trust and debug.

## What's next
- Agencies that maintain hundreds of similar client sites: a fix verified on one site becomes memory that is re-verified on the next.
- Generating checks from the page, with their own verification.
- Measuring the find/fix/prove rate on 20 real open-source sites.

**Source:** https://github.com/miiikkee/proofloop
