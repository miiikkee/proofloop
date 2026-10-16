"""SurrealDB Agent Memory: recall verified fixes before diagnosis, record outcomes after.

Memory is a hint, never an authority: recalled text goes to the LLM as untrusted
context, every proposal still passes the safety gate, and only browser
verification decides pass/fail. Remembered text is built from gate-approved
patch fields and check names only (no URLs, tokens, or page content).
"""
from __future__ import annotations

import os

LABEL_APP = "app=proofloop"


class FixMemory:
    def __init__(self) -> None:
        self._m = None
        if all(os.environ.get(k) for k in ("SURREAL_MEMORY_API_KEY", "SURREAL_MEMORY_ENDPOINT")):
            from surrealdb.memory import Memory

            self._m = Memory(
                context=os.environ.get("SURREAL_MEMORY_CONTEXT", "proofloop"),
                endpoint=os.environ["SURREAL_MEMORY_ENDPOINT"],
                api_key=os.environ["SURREAL_MEMORY_API_KEY"],
                timeout=20.0,
            )

    @property
    def enabled(self) -> bool:
        return self._m is not None

    def recall(self, failing_checks: list[dict], k: int = 5) -> list[dict]:
        if not self._m:
            return []
        symptoms = "; ".join(f"{c['name']}: {c['detail'][:160]}" for c in failing_checks)
        res = self._m.recall(
            f"How was this website acceptance failure fixed before? {symptoms}",
            k=k, labels=[LABEL_APP],
        )
        return [{"id": h.id, "score": round(h.score, 3), "source": h.source, "text": h.text[:600]}
                for h in res.hits]

    def remember_outcome(self, *, run_id: str, scenario: str, failing_checks: list[str], symptom: str,
                         proposal: dict | None, outcome: str, candidate: str) -> str | None:
        """outcome: verified | browser_failed | sandbox_failed | rejected."""
        if not self._m or not proposal:
            return None
        edit = (f"in {proposal['file_path']} replace {proposal['find_text']!r} "
                f"with {proposal['replace_text']!r}")
        if outcome == "verified":
            text = (f"ProofLoop VERIFIED FIX (run {run_id}). Failing check(s) {', '.join(failing_checks)} "
                    f"with symptom: {symptom}. Root cause: {proposal['root_cause']} Fix that worked: {edit}. "
                    f"Independently verified in a cloud browser: candidate {candidate} checks passed. "
                    f"This supersedes any earlier failed attempts for the same symptom.")
        else:
            text = (f"ProofLoop FAILED FIX ATTEMPT (run {run_id}, outcome={outcome}). For failing check(s) "
                    f"{', '.join(failing_checks)} with symptom: {symptom}, the edit {edit} did NOT fix it. "
                    f"Do not repeat this edit.")
        res = self._m.remember(
            text,
            labels=[LABEL_APP, f"kind={'verified_fix' if outcome == 'verified' else 'failed_fix'}",
                    f"scenario={scenario}", f"run={run_id}"] + [f"check={c}" for c in failing_checks],
        )
        return res.turn_id or res.chunk_id or res.session_id
