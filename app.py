"""ProofLoop CLI entry point.

    python app.py                 # full run, sandbox deleted afterwards
    python app.py --keep-sandbox  # leave sandbox up for a live demo (signed URLs expire in 1h)
"""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.orchestrator import run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-sandbox", action="store_true")
    rep = run(keep_sandbox=ap.parse_args().keep_sandbox)
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
