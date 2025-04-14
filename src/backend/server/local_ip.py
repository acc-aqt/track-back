"""Get the local IPv4 address of the machine running the script."""

import ipaddress
import os
import platform
import shlex
import subprocess


class LocalIpRetrievalError(Exception):
    """Custom exception for local IP retrieval errors."""


def get_local_ip() -> str:
    """Get the local IPv4 address of the machine running the script."""
    local_ipv4 = ""
    operating_system_kind = platform.system()
    if operating_system_kind == "Darwin":  # macOS
        local_ipv4 = _run_shell_command("ipconfig getifaddr en0", True).stdout.strip()
    elif operating_system_kind == "Windows":
        for line in _run_shell_command(
            'netsh ip show address | findstr "IP Address"', True
        ).stdout.split(os.linesep):
            local_ipv4_or_empty = line.removeprefix("IP Address:").strip()
            if local_ipv4_or_empty:
                local_ipv4 = local_ipv4_or_empty
                break
    else:  # Linux
        local_ipv4 = _run_shell_command(
            "hostname -I | awk '{print $1}'", True
        ).stdout.strip()  # TODO(Alex): not tested under Linux...

    try:
        ipaddress.IPv4Address(local_ipv4)
    except ipaddress.AddressValueError as e:
        raise LocalIpRetrievalError(
            "Could not get local network IPv4 address for Expo Fronted"
        ) from e

    if local_ipv4.startswith("127.0."):
        raise LocalIpRetrievalError(
            "Could not get correct local network IPv4 address"
            "for Expo Fronted, got {local_ipv4}"
        )

    return local_ipv4


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
