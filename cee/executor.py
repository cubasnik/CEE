"""Sandboxed code executor for the Cloud Execution Environment."""

import subprocess
import sys
import tempfile
import os
from typing import Tuple, Optional

from .models import Language


# Maximum output size (bytes) to prevent memory exhaustion
_MAX_OUTPUT_BYTES = 1 * 1024 * 1024  # 1 MiB


def _build_command(language: Language, script_path: str) -> list[str]:
    """Return the command list to run the script for the given language."""
    if language == Language.python:
        return [sys.executable, script_path]
    if language == Language.bash:
        return ["/bin/bash", script_path]
    raise ValueError(f"Unsupported language: {language}")  # pragma: no cover


def _script_extension(language: Language) -> str:
    if language == Language.python:
        return ".py"
    return ".sh"


def execute(
    language: Language,
    code: str,
    timeout: int,
    stdin: Optional[str] = None,
) -> Tuple[str, str, int, bool]:
    """Execute *code* in the given *language* with a *timeout*.

    Returns ``(stdout, stderr, exit_code, timed_out)``.
    """
    suffix = _script_extension(language)
    script_path = None
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(code)
        script_path = tmp.name

    try:
        cmd = _build_command(language, script_path)
        stdin_bytes = stdin.encode() if stdin else None
        try:
            result = subprocess.run(
                cmd,
                input=stdin_bytes,
                capture_output=True,
                timeout=timeout,
            )
            stdout = result.stdout[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            stderr = result.stderr[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            return stdout, stderr, result.returncode, False
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or b"")[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            stderr = (exc.stderr or b"")[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            return stdout, stderr, -1, True
    finally:
        if script_path is not None:
            try:
                os.unlink(script_path)
            except OSError:
                pass
