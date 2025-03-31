"""Module containing utility functions for the project."""

from datetime import datetime


def extract_year(date_str: str) -> int:
    """Extracts the year from a date string and handles different date formats."""
    formats = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")
