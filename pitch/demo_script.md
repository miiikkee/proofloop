# 3-minute pitch

**0:00–0:25 Problem.** "Teams find broken web flows after customers complain. AI agents can propose fixes, but confidence isn't proof. ProofLoop finds the failure and proves a safe fix works before anything reaches production."

**0:25–0:45 The site.** Show the Acme Studio demo site and the contact form. "This form has one bug. We planted it, and the agent doesn't know what it is."

**0:45–1:35 Detect.** Run `python app.py`. Point out: a Daytona sandbox spins up in about 5 s with separate baseline and candidate copies. Anchor's cloud browser hits the signed preview URL. Baseline is **2/3**: Send is clicked, but the page stays on /contact and no "Thank you" appears.

**1:35–2:10 Diagnose, patch, verify.** Claude on Bedrock reads the evidence and the source and returns JSON: root cause, a one-line edit, confidence 0.97. The safety gate checks the allowlist and exact match. The patch goes into the candidate copy only. Sandbox tests pass. A fresh Anchor session re-runs the same checks: **3/3**. Show `artifacts/before_after.png` and `patch.diff`.

**(+15 s) Memory.** Point at the `memory` log lines: SurrealDB recalls the earlier verified fix for the same symptom, traceable to its run id. The model uses it as a hint, not an answer. On a different bug it says the hint doesn't apply.

**2:10–2:35 Evidence.** Show `run_report.json`: 2/3 to 3/3, about 35–40 s end to end, baseline_copy_modified=false. Show the Arize AX trace with one span per step.

**2:35–3:00 Safety and vision.** "The model never runs shell commands, edits only allowlisted files, and never merges. Pass/fail comes from the browser, not the model. Next: run it on every preview deploy in CI."

**Q&A one-liner. "Why not just Playwright?"** "Playwright tells you a journey failed. ProofLoop links the browser evidence to source, proposes a bounded fix in an isolated sandbox, and independently proves it works."
