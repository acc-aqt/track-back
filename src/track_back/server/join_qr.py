"""Build the join link and its QR code that open the Web UI with a Game Session preselected."""

import io
from urllib.parse import quote

import segno

QR_DARK = "#1a1a2e"
QR_LIGHT = "#8AABDB"


def join_path(
    session_name: str, username: str | None = None, *, host: bool = False
) -> str:
    """Build the Web UI path that joins ``session_name``.

    Parameters
    ----------
    session_name : str
        The Game Session to join.
    username : str, optional
        The username to join with.
    host : bool
        Whether the joining Player is the Host.

    Returns
    -------
    str
        ``/?join=<session>``, plus ``&username=<username>`` and ``&host=1`` if given.
    """
    path = f"/?join={quote(session_name, safe='')}"
    if username is not None:
        path += f"&username={quote(username, safe='')}"
    if host:
        path += "&host=1"
    return path


def render_svg(url: str) -> str:
    """Render ``url`` as a scalable QR code SVG.

    Parameters
    ----------
    url : str
        The text the QR code encodes.

    Returns
    -------
    str
        An SVG document with a ``viewBox``, drawn in the Web UI's dark text colour
        on its light control colour, so it scales with CSS and matches the panels.
    """
    buffer = io.BytesIO()
    segno.make_qr(url).save(
        buffer,
        kind="svg",
        scale=4,
        dark=QR_DARK,
        light=QR_LIGHT,
        omitsize=True,
        xmldecl=False,
    )
    return buffer.getvalue().decode("utf-8")
