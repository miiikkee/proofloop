"""ProofLoop CLI entry point.

    python app.py                 # full run, sandbox deleted afterwards
    python app.py --scenario all  # run every injected-bug scenario
    python app.py --keep-sandbox  # leave sandbox up for a live demo (signed URLs expire in 1h)
"""
import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.orchestrator import ART, run  # noqa: E402
from agent.scenarios import DEFAULT, SCENARIOS  # noqa: E402


def suite() -> int:
    """Run every bug scenario end to end, each in its own fresh sandbox."""
    rows = []
    for name, sc in SCENARIOS.items():
        print(f"\n########## scenario: {name} ##########")
        rep = run(scenario=name, art=ART / "suite" / name)
        rows.append({
            "scenario": name, "injected_bug": sc["description"],
            "baseline": f"{rep.baseline_passed}/{rep.baseline_total}",
            "candidate": f"{rep.candidate_passed}/{rep.candidate_total}",
            "attempts": rep.patch_attempts, "verified_fix": rep.verified_fix,
            "baseline_modified": rep.safety.get("baseline_copy_modified"),
            "runtime_s": round(rep.total_runtime_ms / 1000, 1),
            "root_cause": (rep.proposals[-1].get("proposal") or {}).get("root_cause", "") if rep.proposals else "",
            "errors": rep.errors,
        })
    (ART / "suite").mkdir(parents=True, exist_ok=True)
    (ART / "suite" / "suite_summary.json").write_text(json.dumps(rows, indent=2))
    print("\n================ ProofLoop suite ================")
    print(f"{'scenario':<20}{'baseline':>9}{'candidate':>10}{'tries':>6}{'verified':>9}{'secs':>7}")
    for r in rows:
        print(f"{r['scenario']:<20}{r['baseline']:>9}{r['candidate']:>10}{r['attempts']:>6}{str(r['verified_fix']):>9}{r['runtime_s']:>7}")
    ok = sum(r["verified_fix"] for r in rows)
    print(f"verified fixes: {ok}/{len(rows)}   summary: artifacts/suite/suite_summary.json")
    return 0 if ok == len(rows) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-sandbox", action="store_true")
    ap.add_argument("--scenario", default=DEFAULT, choices=[*SCENARIOS, "all"])
    args = ap.parse_args()
    if args.scenario == "all":
        return suite()
    rep = run(keep_sandbox=args.keep_sandbox, scenario=args.scenario)
    print("\n================ ProofLoop result ================")
    print(f"browser            : {rep.browser_provider}")
    print(f"llm                : {rep.llm_provider or '-'}")
    print(f"daytona sandbox    : {rep.sandbox_id}")
    print(f"baseline checks    : {rep.baseline_passed}/{rep.baseline_total}")
    print(f"candidate checks   : {rep.candidate_passed}/{rep.candidate_total}")
    print(f"patch attempts     : {rep.patch_attempts}/2")
    print(f"verified fix       : {rep.verified_fix}")
    print(f"patch status       : {rep.safety.get('patch_status')}")
    print(f"baseline modified  : {rep.safety.get('baseline_copy_modified')}")
    print(f"total runtime      : {rep.total_runtime_ms / 1000:.1f}s  {rep.step_timings_ms}")
    print(f"artifacts          : artifacts/run_report.json, {rep.patch_diff_path}, {rep.comparison_image_path}")
    for e in rep.errors:
        print(f"ERROR              : {e}")
    return 0 if rep.verified_fix else 1


if __name__ == "__main__":
    sys.exit(main())
