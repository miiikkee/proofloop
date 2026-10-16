"""Daytona sandbox: separate baseline and candidate copies, fixed commands only."""
from __future__ import annotations

import os
import time
from pathlib import Path

from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig, SessionExecuteRequest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_FILES = [
    "fixture_site/app.py",
    "fixture_site/requirements.txt",
    "fixture_site/templates/index.html",
    "fixture_site/templates/contact.html",
    "fixture_site/templates/success.html",
]
BASELINE_PORT = 3000
CANDIDATE_PORT = 3001
PREVIEW_TTL_S = 3600

# Developer-defined checks run inside the candidate copy. The LLM cannot change these.
SANDBOX_CHECKS = {
    "py_compile": "python -m py_compile app.py",
    "flask_routes": (
        "python -c \"import app; c=app.app.test_client(); "
        "assert c.get('/').status_code==200; assert c.get('/contact').status_code==200; "
        "r=c.post('/contact', data={'name':'QA','email':'qa@example.com','message':'hi'}); "
        "assert b'Thank you' in r.data; print('routes ok')\""
    ),
    "templates_render": (
        "python -c \"import app; c=app.app.test_client(); "
        "[c.get(p).data.decode() for p in ('/','/contact')]; print('templates ok')\""
    ),
}


class SandboxRig:
    def __init__(self) -> None:
        self.daytona = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
        self.sandbox = None
        self.home = ""
        self.signed_tokens: list[tuple[int, str]] = []

    @property
    def id(self) -> str | None:
        return self.sandbox.id if self.sandbox else None

    def create(self) -> None:
        # public=False: previews are reached only through expiring signed URLs.
        self.sandbox = self.daytona.create(
            CreateSandboxFromSnapshotParams(
                language="python",
                labels={"app": "proofloop"},
                auto_stop_interval=30,
                ephemeral=True,
            ),
            timeout=180,
        )
        self.home = self.sandbox.get_work_dir().rstrip("/")

    def _dir(self, copy: str) -> str:
        return f"{self.home}/{copy}"

    def stage(self, copy: str, files: dict[str, str] | None = None) -> None:
        files = files or {rel: (ROOT / rel).read_text() for rel in FIXTURE_FILES}
        for rel, text in files.items():
            dest = f"{self._dir(copy)}/{rel.removeprefix('fixture_site/')}"
            self.sandbox.fs.create_folder(dest.rsplit("/", 1)[0], "755")
            self.sandbox.fs.upload_file(text.encode(), dest)

    def install(self) -> None:
        r = self.sandbox.process.exec("pip install -q flask==3.0.3", timeout=180)
        if r.exit_code != 0:
            raise RuntimeError(f"pip install failed: {r.result[-500:]}")

    def read(self, copy: str, rel: str) -> str:
        return self.sandbox.fs.download_file(f"{self._dir(copy)}/{rel.removeprefix('fixture_site/')}").decode()

    def write(self, copy: str, rel: str, text: str) -> None:
        self.sandbox.fs.upload_file(text.encode(), f"{self._dir(copy)}/{rel.removeprefix('fixture_site/')}")

    def run_checks(self, copy: str) -> list[dict]:
        out = []
        for name, cmd in SANDBOX_CHECKS.items():
            t0 = time.monotonic()
            r = self.sandbox.process.exec(cmd, cwd=self._dir(copy), timeout=60)
            out.append({
                "name": name,
                "passed": r.exit_code == 0,
                "detail": (r.result or "").strip()[-300:],
                "duration_ms": int((time.monotonic() - t0) * 1000),
            })
        return out

    def serve(self, copy: str, port: int) -> str:
        """Start the copy's Flask server and return an expiring signed preview URL."""
        sid = f"serve-{copy}-{port}"
        self.sandbox.process.create_session(sid)
        self.sandbox.process.execute_session_command(
            sid,
            SessionExecuteRequest(command=f"cd {self._dir(copy)} && PORT={port} python app.py", run_async=True),
        )
        for _ in range(30):
            r = self.sandbox.process.exec(f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/", timeout=10)
            if r.result.strip() == "200":
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{copy} server did not start on port {port}")
        signed = self.sandbox.create_signed_preview_url(port, expires_in_seconds=PREVIEW_TTL_S)
        self.signed_tokens.append((port, signed.token))
        return signed.url

    def cleanup(self, delete: bool = True) -> None:
        if not self.sandbox:
            return
        for port, token in self.signed_tokens:
            try:
                self.sandbox.expire_signed_preview_url(port, token)
            except Exception:
                pass
        if delete:
            try:
                self.sandbox.delete()
            except Exception:
                pass
