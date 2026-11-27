"""Render the QR code that opens the Web UI with a Game Session preselected."""

import io

import segno


def render_svg(url: str) -> str:
    """Render ``url`` as a scalable QR code SVG.

    Parameters
    ----------
    url : str
        The text the QR code encodes.

    Returns
    -------
    str
        An SVG document with a ``viewBox`` and a white background, so it scales
        with CSS and stays scannable on dark themes.
    """
    buffer = io.BytesIO()
    segno.make_qr(url).save(
        buffer, kind="svg", scale=4, light="#fff", omitsize=True, xmldecl=False
    )
    return buffer.getvalue().decode("utf-8")
