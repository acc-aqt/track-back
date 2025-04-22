"""Get the local IPv4 address of the machine running the script."""

import platform
import shlex
import subprocess


class LocalIpRetrievalError(Exception):
    """Custom exception for local IP retrieval errors."""


def get_local_ip() -> str:
    """Get the local IPv4 address of the machine running the script."""
    operating_system_kind = platform.system()
    try:
        if operating_system_kind == "Darwin":  # macOS
            return _run_shell_command("ipconfig getifaddr en0", True).stdout.strip()
    except subprocess.CalledProcessError:
        return "local-ip-retrieval-failed"

    return "evaluation-of-local-ip-not-yet-implemented-for-current-os"


def _run_shell_command(
    command: str, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    print(f"Running command: {command}")

    # ruff: noqa: S603
    completed_process = subprocess.run(
        shlex.split(command),
        capture_output=capture_output,
        text=capture_output,
        check=False,
    )
    return completed_process
