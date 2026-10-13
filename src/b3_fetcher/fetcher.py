"""HTTP fetching utilities for the B3 COTAHIST source adapter.

This module builds the canonical distribution URLs for the Historical
Quotations (COTAHIST) files published by B3. It only describes the remote
source — downloads are orchestrated by ``FetcherApp`` (``sync``/``check``).
"""

from __future__ import annotations

from .constants import COTAHIST_BASE_URL, MIN_YEAR


def build_annual_url(year: int) -> str:
    """Build the URL of the annual COTAHIST archive for ``year``.

    Args:
        year: Reference year (``COTAHIST_A<ano>.zip``).

    Returns:
        The remote URL of the annual archive.
    """
    return f"{COTAHIST_BASE_URL}A{year}.zip"


def build_monthly_url(year: int, month: int) -> str:
    """Build the URL of the monthly COTAHIST archive (``AAAMM``).

    Args:
        year: Reference year.
        month: Reference month (1-12).

    Returns:
        The remote URL of the monthly archive.
    """
    return f"{COTAHIST_BASE_URL}M{month:02d}{year}.zip"


def build_daily_url(year: int, month: int, day: int) -> str:
    """Build the URL of the daily COTAHIST archive (``DDMMAAAA``).

    Args:
        year: Reference year.
        month: Reference month (1-12).
        day: Reference day.

    Returns:
        The remote URL of the daily archive.
    """
    return f"{COTAHIST_BASE_URL}D{day:02d}{month:02d}{year}.zip"


def valid_year(year: int, *, current_year: int) -> bool:
    """Return whether ``year`` is within the published COTAHIST coverage.

    Args:
        year: Year to validate.
        current_year: Current calendar year (upper bound, inclusive).

    Returns:
        ``True`` if the year is between :data:`MIN_YEAR` and ``current_year``.
    """
    return MIN_YEAR <= year <= current_year
