"""Discover the addresses other devices can reach this machine on."""

import ipaddress
import logging
import socket

logger = logging.getLogger(__name__)

# Connecting a UDP socket sends no packets; it only selects the outgoing interface.
_ROUTE_PROBE_ADDRESS = ("192.0.2.1", 80)


def lan_ipv4_addresses() -> list[str]:
    """Return this machine's non-loopback IPv4 addresses.

    Returns
    -------
    list[str]
        The addresses, without duplicates, in discovery order.

    Raises
    ------
    OSError
        If the network can't be queried.
    """
    candidates = [*_default_route_address(), *_hostname_addresses()]
    addresses: list[str] = []
    for candidate in candidates:
        if candidate in addresses:
            continue
        if ipaddress.IPv4Address(candidate).is_loopback:
            continue
        addresses.append(candidate)
    return addresses


def lan_ipv4_addresses_or_empty() -> list[str]:
    """Return this machine's non-loopback IPv4 addresses, or none if discovery fails.

    Returns
    -------
    list[str]
        The addresses from `lan_ipv4_addresses`, or an empty list (with a logged
        warning) if the network can't be queried.
    """
    try:
        return lan_ipv4_addresses()
    except OSError:
        logger.warning("Could not discover LAN addresses.", exc_info=True)
        return []


def _default_route_address() -> list[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(_ROUTE_PROBE_ADDRESS)
        except OSError:
            return []
        return [str(probe.getsockname()[0])]


def _hostname_addresses() -> list[str]:
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return [str(info[4][0]) for info in infos]
