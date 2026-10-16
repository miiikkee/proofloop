# 3-minute pitch

**0:00–0:25 Opening and problem.** "Evaluation is the real bottleneck in AI work. AI agents can already propose fixes, but a model's confidence isn't proof. ProofLoop accepts a fix only on independent evidence: it reproduces the failure in a real browser, tries the fix in an isolated copy, and proves the user journey works again before anyone adopts it."

**0:25–0:45 The site.** Show the Acme Studio demo site and the contact form. "The site is deliberately simple, and we planted the bugs ourselves. What we're demonstrating is the acceptance loop, not how hard the bug is."

**0:45–1:35 Detect.** Run `python app.py`. Point out: a Daytona sandbox spins up in about 5 s with separate baseline and candidate copies. Anchor's cloud browser hits the signed preview URL. Baseline is **2/3**: Send is clicked, but the page stays on /contact and no "Thank you" appears.

**1:35–2:10 Diagnose, patch, verify.** Claude on Bedrock reads the evidence and the source and returns JSON: root cause, a one-line edit, confidence 0.97. The safety gate checks the allowlist and exact match. The patch goes into the candidate copy only. Sandbox tests pass. A fresh Anchor session re-runs the same checks: **3/3**. Show `artifacts/before_after.png` and `patch.diff`.

**(+15 s) Memory.** Point at the `memory` log lines: SurrealDB recalls the earlier verified fix for the same symptom, traceable to its run id. The model uses it as a hint, not an answer. On a different bug it says the hint doesn't apply.

**2:10–2:35 Evidence.** Show `run_report.json`: 2/3 to 3/3, about 35–40 s end to end, baseline_copy_modified=false. Show the Arize AX trace with one span per step.

**2:35–3:00 Safety and vision.** "The model never runs shell commands, edits only allowlisted files, and never merges. Pass/fail comes from the browser, not the model. Next: run it on every preview deploy in CI."

## Q&A prep

**"There are already tools for this: QA Wolf, Momentic, Meticulous, Claude Code or Codex with Playwright."**
"Others can fix too. What we add is that a fix is accepted only on independent evidence: it runs in an isolated copy, the original is never touched, a person approves it, and every outcome is logged. That acceptance discipline is what lets a team trust an agent's fix."

**"Who writes the checks?"** (most likely question)
"Today the developer does, on purpose, because checks the model writes for itself can't be trusted to judge its own fix. The next step is to generate checks from the page, but those generated checks need their own verification. That's where we're headed."

**"The bugs are planted and trivial."**
"Yes, on purpose. We're proving the verification loop: a fix is accepted on independent evidence, not on the model's confidence. Bug difficulty is the next variable to scale, and the loop doesn't change when it does."

**"Your safety rules would reject real fixes."**
"They're tuned tight for the demo. They define the agent's blast radius, and each team sets that. The point is that the boundary is deterministic and enforced outside the LLM. On a real site the rules become configuration; verification stays the same."

**"What's next?"**
"Pick one real open-source site, have the agent generate checks from the page, and measure how often it finds and fixes a real bug. That number is our next pitch."

**"Why not just Playwright?"**
"Playwright tells you a journey failed. ProofLoop links the browser evidence to source, proposes a bounded fix in an isolated sandbox, and accepts it only when the same independent checks pass."
