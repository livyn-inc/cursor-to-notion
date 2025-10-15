"""Error handling and subprocess utilities."""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional


__all__ = [
    "run_subprocess",
    "run_subprocess_with_env",
    "handle_subprocess_error",
    "exit_with_error",
    "print_error",
    "print_warning",
    "print_user_friendly_error",
    "print_success",
]


def run_subprocess(
    cmd: List[str],
    *,
    capture_output: bool = True,
    text: bool = True,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess with standardized error handling."""
    try:
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            cwd=cwd,
            env=env,
            check=False,  # Don't raise on non-zero exit
        )
    except subprocess.TimeoutExpired:
        print_error(f"Subprocess timed out after {timeout}s: {' '.join(cmd)}")
        raise
    except Exception as e:
        print_error(f"Failed to run subprocess: {' '.join(cmd)} - {e}")
        raise


def run_subprocess_with_env(
    cmd: List[str],
    *,
    capture_output: bool = True,
    text: bool = True,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess with environment variables."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    return run_subprocess(
        cmd,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        cwd=cwd,
        env=env,
    )


def handle_subprocess_error(
    result: subprocess.CompletedProcess,
    cmd: List[str],
    *,
    show_stderr: bool = True,
    show_stdout: bool = False,
    prefix: str = "Subprocess",
) -> None:
    """Handle subprocess errors with consistent messaging."""
    if result.returncode == 0:
        return

    cmd_str = " ".join(cmd)
    print_error(f"{prefix} failed (exit code {result.returncode}): {cmd_str}")

    if show_stdout and result.stdout:
        print(f"STDOUT: {result.stdout.strip()}")

    if show_stderr and result.stderr:
        print(f"STDERR: {result.stderr.strip()}")


def exit_with_error(message: str, exit_code: int = 1) -> None:
    """Exit with an error message."""
    print_error(message)
    sys.exit(exit_code)


def print_error(message: str) -> None:
    """Print an error message with consistent formatting."""
    print(f"❌ Error: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message with consistent formatting."""
    print(f"⚠️ Warning: {message}", file=sys.stderr)


def print_user_friendly_error(message: str, suggestion: str = "") -> None:
    """Print a user-friendly error message with helpful suggestions."""
    print(f"❌ {message}", file=sys.stderr)
    if suggestion:
        print(f"💡 Suggestion: {suggestion}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print a success message with consistent formatting."""
    print(f"✅ {message}")


def check_subprocess_success(
    result: subprocess.CompletedProcess,
    cmd: List[str],
    *,
    show_output: bool = False,
) -> bool:
    """Check if subprocess succeeded and handle errors."""
    if result.returncode == 0:
        if show_output and result.stdout:
            print(result.stdout.strip())
        return True

    handle_subprocess_error(result, cmd, show_stderr=True, show_stdout=show_output)
    return False
