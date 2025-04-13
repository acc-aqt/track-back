"""Contains a function to get the local IPv4 address of the machine running the script."""

import ipaddress
import os
import platform
import subprocess


def _run_shell_command(command: str, capture_output: bool =False) -> None:
    print(f"$ {command}")
    return subprocess.run(
        command,
        shell=True,
        capture_output=capture_output,
        text=capture_output,
        check=False,
    )  # 'shell=True' => Use built-in shell, '/bin/sh' on Linux and Mac, 'cmd.exe' on Windows.


def get_local_ip() -> str:
    """Get the local IPv4 address of the machine running the script."""
    local_ipv4 = None

    operating_system_kind = platform.system()
    if operating_system_kind == "Darwin":
        local_ipv4 = _run_shell_command(
            "ipconfig getifaddr en0", True
        ).stdout.strip()
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
        ).stdout.strip()

    try:
        ipaddress.IPv4Address(local_ipv4)
    except ipaddress.AddressValueError:
        raise Exception(
            "Could not get local network IPv4 address for Expo Fronted"
        )

    if local_ipv4.startswith("127.0."):
        raise Exception(
            f"Could not get correct local network IPv4 address for Expo Fronted, got {local_ipv4}"
        )

    return local_ipv4
