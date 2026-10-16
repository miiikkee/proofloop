# 3-minute pitch (final)

Frame: we are not "better than Claude Code at fixing bugs". ProofLoop is the **acceptance layer**: a fix is accepted only on independent evidence.

## Script

**0:00–0:20 Opening.**
"Evaluation is the real bottleneck in AI work. Agents like Claude Code can already propose fixes. The hard part is trusting them when nobody is watching. ProofLoop accepts an AI fix only on independent evidence, never on the model's confidence."

**0:20–0:35 Setup (show `pitch/flow.png`).**
"Deliberately simple demo site, bugs we planted ourselves. What we're showing is the acceptance loop, not how hard the bug is."

**0:35–1:25 Live run: `python app.py`** (~40 s; narrate while logs scroll)
- "Daytona spins up an isolated sandbox with two copies: the original is never touched, and the candidate is where fixes go."
- "Anchor's cloud browser runs three checks the developer wrote. Two of three pass, and the form never submits."
- "SurrealDB recalls how we fixed similar symptoms before, as a hint and not an answer."
- "Claude on Bedrock returns a structured patch. A deterministic safety gate, outside the model, checks it."
- "Fresh Anchor session, same checks: three of three."

**1:25–1:45 Proof (show `artifacts/before_after.png`).**
"Before: no submit. After: Thank you. Original copy unmodified. The fix waits for a human to approve; no auto-merge."

**1:45–2:10 Evidence (show the Arize trace tree, then SurrealDB Workbench).**
"Every step is traced in Arize: Daytona calls, LLM tokens, pass counts. Every outcome is stored in SurrealDB and traceable to its run. Three different bugs, all fixed and verified on the first attempt."

**2:10–2:40 Guardrails.**
"The model never runs shell commands and never writes the checks that grade it. It edits only allowlisted files. Pass or fail comes from the browser."

**2:40–3:00 Vision.**
"Next: agencies that maintain hundreds of similar client sites. A fix verified on one site becomes memory that's re-verified on the next. That's where agent memory plus independent verification compounds. Find it, fix it, prove it."

## Q&A

**"Claude Code / ChatGPT can already do this."**
"Yes, they can propose fixes, and you could plug one in as our step 4. What we add is acceptance discipline: the proposer never grades its own work, the original is never touched, a person approves, and every outcome is logged. That's what lets a team trust a fix when nobody is watching."

**"QA Wolf, Momentic, Meticulous?"**
"Others can fix too. We're not competing on fixing. We focus on accepting a fix only on independent evidence in an isolated copy, with an audit trail."

**"Who writes the checks?"** (most likely)
"Today the developer does, on purpose, because checks the model writes for itself can't be trusted to judge its own fix. Next is generating checks from the page, but those need their own verification. That's where we're headed."

**"The bugs are planted and trivial."**
"On purpose. We're proving the verification loop; bug difficulty is the next variable, and the loop doesn't change when it scales."

**"Your safety rules would reject real fixes."**
"They're tight for the demo. They define the agent's blast radius, which each team configures. The point is that the boundary is deterministic and enforced outside the LLM."

**"Business model / market?"**
"Agencies managing many similar sites first: per-site monthly, priced on verified fixes. We'd validate by running on 20 real sites and measuring how many real bugs get found, fixed and proven. That number is our next pitch."

**Avoid saying:** "better than Claude Code", "production ready", "guarantees compliance", "accessibility market" (Evinced and Deque already ship AI fixers there).

## Backup if the live run fails
Don't debug on stage. Say "here's a run from earlier" and show `artifacts/before_after.png`, `artifacts/suite/suite_summary.json` and the Arize trace (or the recorded video).
