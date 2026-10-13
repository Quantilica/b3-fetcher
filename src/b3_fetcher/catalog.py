"""B3 COTAHIST unified dataset catalog.

The B3 Historical Quotations series is published as one ZIP per year, so the
catalog exposes a single group (``cotacaohistorica``) partitioned by year,
covering the full history from 1986 up to the current year.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from .constants import DATASET_ID, MIN_YEAR
from .fetcher import build_annual_url

GROUPS = {
    DATASET_ID: {
        "name": "Cotações Históricas da B3 (COTAHIST)",
        "description": (
            "Série histórica de cotações da B3 desde 1986 "
            "(arquivos anuais COTAHIST_A<ano>.zip)."
        ),
    }
}

GROUP_ALIASES: dict[str, list[str]] = {}


def list_datasets(group: str | None = None) -> list[dict[str, Any]]:
    """List the available COTAHIST annual partitions.

    Args:
        group: Optional group name. When provided it must be
            ``cotacaohistorica``.

    Returns:
        One entry dictionary per year, from 1986 to the current year.

    Raises:
        ValueError: If an unknown group is requested.
    """
    if group is not None and group != DATASET_ID:
        raise ValueError(f"Grupo desconhecido: {group!r}")

    current_year = dt.date.today().year
    return [
        {
            "id": f"{DATASET_ID}-{year}",
            "group": DATASET_ID,
            "year": year,
            "url": build_annual_url(year),
            "ext": "zip",
        }
        for year in range(MIN_YEAR, current_year + 1)
    ]
