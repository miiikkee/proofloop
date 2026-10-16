"""Typed records shared across the pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0


@dataclass
class BrowserRun:
    target_url: str
    provider: str  # "anchor" or "local-playwright"
    checks: list[CheckResult]
    screenshot_path: str | None = None
    session_id: str | None = None
    error: str | None = None

    @property
    def passed(self) -> int:
        return sum(c.passed for c in self.checks)

    @property
    def total(self) -> int:
        return len(self.checks)


@dataclass
class PatchProposal:
    root_cause: str
    file_path: str
    find_text: str
    replace_text: str
    reason: str
    confidence: float

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PatchProposal":
        missing = [k for k in cls.__dataclass_fields__ if k not in d]
        if missing:
            raise ValueError(f"patch proposal missing fields: {missing}")
        return cls(
            root_cause=str(d["root_cause"]),
            file_path=str(d["file_path"]),
            find_text=str(d["find_text"]),
            replace_text=str(d["replace_text"]),
            reason=str(d["reason"]),
            confidence=float(d["confidence"]),
        )


@dataclass
class RunReport:
    run_id: str
    target_url: str = ""
    candidate_url: str = ""
    issue_id: str = "contact-form-submit"
    browser_provider: str = ""
    llm_provider: str = ""
    baseline_passed: int = 0
    baseline_total: int = 0
    candidate_passed: int = 0
    candidate_total: int = 0
    patch_attempts: int = 0
    verified_fix: bool = False
    total_runtime_ms: int = 0
    screenshot_before_path: str | None = None
    screenshot_after_path: str | None = None
    comparison_image_path: str | None = None
    patch_diff_path: str | None = None
    sandbox_id: str | None = None
    trace_url: str | None = None
    baseline_checks: list[dict] = field(default_factory=list)
    candidate_checks: list[dict] = field(default_factory=list)
    sandbox_checks: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    step_timings_ms: dict[str, int] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
