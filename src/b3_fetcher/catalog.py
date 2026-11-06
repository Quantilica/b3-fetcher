"""B3 dataset catalog.

``cotacaohistorica`` (COTAHIST) is published as one ZIP per year, covering 1986 up
to the current year. ``derivativos_agro`` (daily, A4 two-step token) and
``indices_carteiras`` (current index portfolios) complete the catalog.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from .constants import (
    DATASET_ID,
    DEFAULT_LOOKBACK_BUSINESS_DAYS,
    FILE_NAMES,
    INDICES,
    LOOKBACK_ENV,
    MIN_YEAR,
)
from .fetcher import build_annual_url
from .source import build_requestname_url, index_url

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

EXPANDED_GROUPS = {
    "derivativos_agro": {
        "name": "Derivativos Agropecuários",
        "description": (
            "Posições em aberto em derivativos (DerivativesOpenPosition), "
            "segmento AGRIBUSINESS: BGI, CCM, ICF, SJC e demais."
        ),
    },
    "indices_carteiras": {
        "name": "Composição de Carteiras de Índices",
        "description": (
            "Composição e pesos teóricos vigentes dos índices da B3 "
            "(IBOV, IBRX100, SMLL, IDIV, IFIX, IFIL)."
        ),
    },
}

# ``btc_posicoes_abertas`` (empréstimo de ativos) não está aqui de propósito: a
# sondagem de 2026-11-03 não achou ``fileName`` do ``requestname`` nem tabela para
# ele. Sem fonte, sem dataset.

EXPANDED_GROUP_ALIASES: dict[str, list[str]] = {
    "derivativos-agro": ["derivativos_agro"],
    "indices-carteiras": ["indices_carteiras"],
}

ALL_GROUPS = {**GROUPS, **EXPANDED_GROUPS}
ALL_GROUP_ALIASES = {**GROUP_ALIASES, **EXPANDED_GROUP_ALIASES}


def business_days(end: dt.date, count: int) -> list[dt.date]:
    """Os ``count`` dias úteis (seg-sex) terminando em ``end``, em ordem crescente.

    Feriados não são conhecidos aqui: a B3 responde 400 para eles e o ``sync``
    os ignora sem erro.
    """
    days: list[dt.date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= dt.timedelta(days=1)
    return sorted(days)


def _lookback() -> int:
    raw = os.environ.get(LOOKBACK_ENV, "").strip()
    try:
        value = int(raw) if raw else DEFAULT_LOOKBACK_BUSINESS_DAYS
    except ValueError:
        value = DEFAULT_LOOKBACK_BUSINESS_DAYS
    return max(1, value)


def list_datasets(
    group: str | None = None, *, today: dt.date | None = None
) -> list[dict[str, Any]]:
    """List the available B3 dataset partitions.

    Args:
        group: Group name or alias (``cotacaohistorica``, ``derivativos_agro``,
            ``indices_carteiras``). ``None`` lists ``cotacaohistorica``.
        today: Reference date (tests); defaults to today.

    Returns:
        Entries for the requested group. ``derivativos_agro`` lists one entry per
        business day of the lookback window (``B3_LOOKBACK_DAYS``, default 5);
        ``indices_carteiras`` lists one entry per index (the endpoint only serves
        the current portfolio).

    Raises:
        ValueError: If an unknown group is requested.
    """
    if group is not None:
        canonical_group = EXPANDED_GROUP_ALIASES.get(group, [group])[0]
        if canonical_group not in ALL_GROUPS:
            raise ValueError(f"Grupo desconhecido: {group!r}")
    else:
        canonical_group = DATASET_ID

    today = today or dt.date.today()

    if canonical_group == DATASET_ID:
        return [
            {
                "id": f"{DATASET_ID}-{year}",
                "group": DATASET_ID,
                "year": year,
                "url": build_annual_url(year),
                "ext": "zip",
            }
            for year in range(MIN_YEAR, today.year + 1)
        ]

    if canonical_group == "derivativos_agro":
        return [
            {
                "id": f"derivativos_agro-{day.isoformat()}",
                "group": "derivativos_agro",
                "dataset_id": "derivativos_agro",
                "date": day.isoformat(),
                "year": day.year,
                "file_name": FILE_NAMES["derivativos_agro"],
                "url": build_requestname_url(FILE_NAMES["derivativos_agro"], day),
                "protocol": "requestname",
                "ext": "csv",
            }
            for day in business_days(today, _lookback())
        ]

    # indices_carteiras
    return [
        {
            "id": f"indices_carteiras-{indice}",
            "group": "indices_carteiras",
            "dataset_id": "indices_carteiras",
            "indice": indice,
            "date": today.isoformat(),
            "year": today.year,
            "url": index_url(indice),
            "protocol": "portfolio",
            "ext": "json",
        }
        for indice in INDICES
    ]
