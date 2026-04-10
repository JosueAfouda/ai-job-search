from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class CodexError(RuntimeError):
    pass


class CodexClient:
    def __init__(
        self,
        cwd: Path,
        enabled: bool = True,
        timeout_seconds: int = 180,
    ) -> None:
        self.cwd = cwd
        self.enabled = enabled and os.environ.get("CAREER_OPS_DISABLE_CODEX") != "1"
        self.timeout_seconds = timeout_seconds
        self.binary = os.environ.get("CAREER_OPS_CODEX_BIN", "codex")
        self.model = os.environ.get("CODEX_MODEL")

    def run_json(self, prompt: str, schema_path: Path) -> dict[str, Any]:
        output = self.run_text(prompt, schema_path=schema_path, timeout_seconds=120)
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = _extract_json(output)
        if not isinstance(parsed, dict):
            raise CodexError("Codex did not return a JSON object")
        return parsed

    def run_text(
        self,
        prompt: str,
        schema_path: Path | None = None,
        timeout_seconds: int | None = None,
    ) -> str:
        if not self.enabled:
            raise CodexError("Codex subprocess calls are disabled")

        with tempfile.NamedTemporaryFile("r", encoding="utf-8", delete=True) as result_file:
            cmd = [
                self.binary,
                "--ask-for-approval",
                "never",
                "-c",
                'model_reasoning_effort="low"',
                "exec",
                "--cd",
                str(self.cwd),
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--output-last-message",
                result_file.name,
            ]
            if self.model:
                cmd.extend(["--model", self.model])
            if schema_path:
                cmd.extend(["--output-schema", str(schema_path)])
            cmd.append("-")

            try:
                proc = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds or self.timeout_seconds,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                raise CodexError(str(exc)) from exc

            result_file.seek(0)
            output = result_file.read().strip() or proc.stdout.strip()
            if proc.returncode != 0:
                stderr = proc.stderr.strip().splitlines()
                detail = stderr[-1] if stderr else f"exit code {proc.returncode}"
                raise CodexError(detail)
            if not output:
                raise CodexError("Codex returned an empty response")
            return output


def _extract_json(text: str) -> Any:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise CodexError("No JSON object found in Codex output")
    return json.loads(text[start : end + 1])
