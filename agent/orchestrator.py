"""ProofLoop state machine: detect -> diagnose -> patch -> test -> verify -> report."""
from __future__ import annotations

import difflib
import json
import re
import time
import uuid
from pathlib import Path

from agent import observability as obs
from agent.browser import default_provider, run_checks
from agent.diagnose import propose_patch, provider as llm_provider
from agent.repair import BASELINE_PORT, CANDIDATE_PORT, SandboxRig
from agent.safety import ALLOWED_FILES, MAX_ATTEMPTS, PatchRejected, apply_patch
from agent.schemas import RunReport

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts"
READONLY_CONTEXT = ["fixture_site/app.py"]


def redact_url(url: str) -> str:
    """Signed preview hostnames embed an access token; keep only the provider domain."""
    return re.sub(r"https://[^.]+\.", "https://<signed-preview>.", url)


def log(step: str, msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {step:<9} {msg}", flush=True)


def _checks_table(run) -> list[dict]:
    return [c.__dict__ for c in run.checks]


def _comparison_image(before: str, after: str, out: Path, label_b: str, label_a: str) -> str | None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    a, b = Image.open(before), Image.open(after)
    h = max(a.height, b.height) + 40
    canvas = Image.new("RGB", (a.width + b.width + 20, h), "white")
    canvas.paste(a, (0, 40))
    canvas.paste(b, (a.width + 20, 40))
    d = ImageDraw.Draw(canvas)
    d.text((10, 12), label_b, fill=(200, 30, 30))
    d.text((a.width + 30, 12), label_a, fill=(20, 140, 60))
    canvas.save(out)
    return str(out.relative_to(ROOT))


def run(keep_sandbox: bool = False) -> RunReport:
    t_start = time.monotonic()
    ART.mkdir(exist_ok=True)
    rep = RunReport(run_id=time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6])
    rep.browser_provider = default_provider()
    rep.safety = {
        "allowed_files": sorted(ALLOWED_FILES),
        "max_attempts": MAX_ATTEMPTS,
        "model_shell_commands_executed": 0,
        "baseline_copy_modified": False,
        "production_writes": 0,
        "auto_merge": False,
        "patch_status": "not_proposed",
    }
    tracing = obs.init()
    log("init", f"browser={rep.browser_provider} tracing={'arize' if tracing else 'off'} run_id={rep.run_id}")

    def timed(name):
        class T:
            def __enter__(s):
                s.t = time.monotonic()
            def __exit__(s, *a):
                rep.step_timings_ms[name] = rep.step_timings_ms.get(name, 0) + int((time.monotonic() - s.t) * 1000)
        return T()

    rig = SandboxRig()
    with obs.span("proofloop.run", run_id=rep.run_id) as root:
        try:
            # 1. Provision isolated sandbox with two separate copies.
            with timed("provision"), obs.span("provision", kind="TOOL"):
                rig.create()
                rep.sandbox_id = rig.id
                rig.install()
                rig.stage("baseline")
                rig.stage("candidate")
                baseline_url = rig.serve("baseline", BASELINE_PORT)
            rep.target_url = redact_url(baseline_url)
            log("provision", f"Daytona sandbox {rig.id} ready; baseline served on :{BASELINE_PORT}")

            # 2. Detect: baseline acceptance in the browser.
            with timed("detect"), obs.span("detect", kind="TOOL", browser=rep.browser_provider) as s:
                before = run_checks(baseline_url, str(ART / "baseline.png"))
                obs.set_attrs(s, passed=before.passed, total=before.total)
            if before.error:
                raise RuntimeError(f"baseline browser run failed: {before.error}")
            rep.baseline_passed, rep.baseline_total = before.passed, before.total
            rep.baseline_checks = _checks_table(before)
            rep.screenshot_before_path = "artifacts/baseline.png"
            for c in before.checks:
                log("detect", f"{'PASS' if c.passed else 'FAIL'} {c.name}  {c.detail[:110]}")
            log("detect", f"baseline {before.passed}/{before.total} via {before.provider}")
            failing = [c for c in before.checks if not c.passed]
            if not failing:
                log("detect", "no failures; nothing to repair")
                return rep

            evidence = {
                "browser": before.provider,
                "failed_checks": [c.__dict__ for c in failing],
                "passed_checks": [c.name for c in before.checks if c.passed],
                "test_steps_for_failed_check": [
                    "goto /contact", "fill #name, #email, #message", "click #send",
                    "expect text 'Thank you' within 5s",
                ],
                "screenshot": rep.screenshot_before_path,
            }
            rep.llm_provider = llm_provider()
            editable = {p: rig.read("baseline", p) for p in sorted(ALLOWED_FILES)}
            readonly = {p: rig.read("baseline", p) for p in READONLY_CONTEXT}
            prior: list[str] = []

            for attempt in range(1, MAX_ATTEMPTS + 1):
                rep.patch_attempts = attempt
                record: dict = {"attempt": attempt}
                rep.proposals.append(record)
                # 3. Diagnose.
                with timed("diagnose"), obs.span("diagnose", kind="LLM", attempt=attempt) as s:
                    try:
                        proposal, model = propose_patch(evidence, editable, readonly, prior)
                    except Exception as e:
                        record["error"] = f"diagnose failed: {e}"
                        prior.append(record["error"])
                        log("diagnose", record["error"])
                        continue
                    rep.llm_provider = model
                    record["proposal"] = proposal.__dict__
                    obs.set_attrs(s, root_cause=proposal.root_cause, file_path=proposal.file_path,
                                  confidence=proposal.confidence)
                log("diagnose", f"[{model}] {proposal.root_cause}")
                log("diagnose", f"edit {proposal.file_path}: {proposal.find_text!r} -> {proposal.replace_text!r} (conf {proposal.confidence})")

                # 4. Patch the candidate copy only, after safety validation.
                with timed("patch"), obs.span("patch", kind="TOOL", attempt=attempt) as s:
                    original = editable.get(proposal.file_path, "")
                    try:
                        patched = apply_patch(proposal, original)
                    except PatchRejected as e:
                        record["rejected"] = str(e)
                        prior.append(f"{json.dumps(proposal.__dict__)} was REJECTED by safety gate: {e}")
                        obs.set_attrs(s, rejected=str(e))
                        log("patch", f"REJECTED: {e}")
                        continue
                    for p, text in editable.items():  # reset candidate to baseline, then apply
                        rig.write("candidate", p, text)
                    rig.write("candidate", proposal.file_path, patched)
                    diff = "".join(difflib.unified_diff(
                        original.splitlines(True), patched.splitlines(True),
                        f"a/{proposal.file_path}", f"b/{proposal.file_path}"))
                    (ART / "patch.diff").write_text(diff)
                    rep.patch_diff_path = "artifacts/patch.diff"
                    record["diff"] = diff
                log("patch", "applied to sandbox candidate copy (baseline untouched)")

                # 5. Developer-defined checks inside the sandbox.
                with timed("test"), obs.span("test", kind="TOOL", attempt=attempt) as s:
                    rep.sandbox_checks = rig.run_checks("candidate")
                    ok = all(c["passed"] for c in rep.sandbox_checks)
                    obs.set_attrs(s, passed=ok)
                log("test", " ".join(f"{c['name']}={'ok' if c['passed'] else 'FAIL'}" for c in rep.sandbox_checks))
                if not ok:
                    prior.append(f"{json.dumps(proposal.__dict__)} broke sandbox checks: {rep.sandbox_checks}")
                    continue

                # 6. Independent browser verification of the candidate preview.
                with timed("verify"), obs.span("verify", kind="TOOL", attempt=attempt) as s:
                    # New port per attempt so Flask never serves stale cached templates.
                    cand_url = rig.serve("candidate", CANDIDATE_PORT + attempt - 1)
                    rep.candidate_url = redact_url(cand_url)
                    after = run_checks(cand_url, str(ART / "candidate.png"))
                    obs.set_attrs(s, passed=after.passed, total=after.total)
                if after.error:
                    raise RuntimeError(f"candidate browser run failed: {after.error}")
                rep.candidate_passed, rep.candidate_total = after.passed, after.total
                rep.candidate_checks = _checks_table(after)
                rep.screenshot_after_path = "artifacts/candidate.png"
                for c in after.checks:
                    log("verify", f"{'PASS' if c.passed else 'FAIL'} {c.name}  {c.detail[:110]}")
                log("verify", f"candidate {after.passed}/{after.total} via {after.provider}")
                if after.passed == after.total:
                    rep.verified_fix = True
                    break
                prior.append(f"{json.dumps(proposal.__dict__)} applied but browser still failed: "
                             f"{[c.detail for c in after.checks if not c.passed]}")

            rep.safety["patch_status"] = "verified_awaiting_human_approval" if rep.verified_fix else "unverified_discarded"
            if rep.screenshot_before_path and rep.screenshot_after_path:
                rep.comparison_image_path = _comparison_image(
                    str(ART / "baseline.png"), str(ART / "candidate.png"), ART / "before_after.png",
                    f"BEFORE (baseline) {rep.baseline_passed}/{rep.baseline_total}",
                    f"AFTER (candidate) {rep.candidate_passed}/{rep.candidate_total}")
            obs.set_attrs(root, verified_fix=rep.verified_fix, baseline_passed=rep.baseline_passed,
                          candidate_passed=rep.candidate_passed)
        except Exception as e:
            rep.errors.append(f"{type(e).__name__}: {e}")
            log("error", rep.errors[-1])
        finally:
            # Confirm the reference copy was never modified.
            try:
                rep.safety["baseline_copy_modified"] = any(
                    rig.read("baseline", p) != (ROOT / p).read_text() for p in ALLOWED_FILES)
            except Exception:
                pass
            if keep_sandbox:
                log("cleanup", f"keeping sandbox {rig.id} for demo; signed URLs expire in 1h")
            else:
                rig.cleanup()
                log("cleanup", "signed preview URLs expired, sandbox deleted")
            rep.total_runtime_ms = int((time.monotonic() - t_start) * 1000)
            if tracing:
                rep.trace_url = "https://app.arize.com (project: proofloop)"
                obs.flush()
            (ART / "run_report.json").write_text(json.dumps(rep.to_dict(), indent=2))
    return rep
