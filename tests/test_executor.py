"""Tests for the code executor."""

import pytest
from cee.executor import execute
from cee.models import Language


def test_python_hello_world():
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, 'print("hello")', timeout=5
    )
    assert exit_code == 0
    assert stdout.strip() == "hello"
    assert stderr == ""
    assert not timed_out


def test_python_stdin():
    code = "import sys\nprint(sys.stdin.read().strip())"
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, code, timeout=5, stdin="world"
    )
    assert exit_code == 0
    assert stdout.strip() == "world"
    assert not timed_out


def test_python_stderr():
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, "import sys\nsys.stderr.write('err')", timeout=5
    )
    assert exit_code == 0
    assert "err" in stderr
    assert not timed_out


def test_python_non_zero_exit():
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, "raise SystemExit(42)", timeout=5
    )
    assert exit_code == 42
    assert not timed_out


def test_python_syntax_error():
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, "def (", timeout=5
    )
    assert exit_code != 0
    assert "SyntaxError" in stderr
    assert not timed_out


def test_python_timeout():
    stdout, stderr, exit_code, timed_out = execute(
        Language.python, "import time\ntime.sleep(60)", timeout=1
    )
    assert timed_out
    assert exit_code == -1
    assert stdout == ""
    assert stderr == ""


def test_bash_echo():
    stdout, stderr, exit_code, timed_out = execute(
        Language.bash, "echo hello", timeout=5
    )
    assert exit_code == 0
    assert stdout.strip() == "hello"
    assert not timed_out


def test_bash_non_zero_exit():
    stdout, stderr, exit_code, timed_out = execute(
        Language.bash, "exit 3", timeout=5
    )
    assert exit_code == 3
    assert not timed_out
