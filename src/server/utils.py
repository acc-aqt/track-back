"""Module containing utility functions and decorators."""

# ruff: noqa: ANN002, ANN003, ANN202

import logging
import traceback
from collections.abc import Awaitable, Callable
from functools import wraps

from fastapi import HTTPException


def exception_handling(
    func: Callable[..., Awaitable],  # type: ignore
) -> Callable[..., Awaitable]:  # type: ignore
    """Wrap functions to raise HTTPException on errors."""

    @wraps(func)
    async def wrapper(*args, **kwargs):  # type: ignore
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Already an HTTP error → re-raise untouched
            raise
        except Exception as exc:
            tb_str = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            logging.error("Unhandled exception in %s: %s", func.__name__, tb_str)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(exc),
                    "stacktrace": tb_str,
                },
            ) from exc

    return wrapper
