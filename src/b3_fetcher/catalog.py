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

EXPANDED_GROUPS = {
    "btc_posicoes_abertas": {
        "name": "Empréstimo de Ativos (BTC)",
        "description": "Posições em aberto de empréstimo de ações (short interest).",
    },
    "derivativos_agro": {
        "name": "Derivativos Agropecuários",
        "description": "Ajustes diários e contratos em aberto (BGI, CCM, ICF, SJC).",
    },
    "indices_carteiras": {
        "name": "Composição de Carteiras de Índices",
        "description": (
            "Composição e pesos teóricos dos índices da B3 (IBOV, IBRX100, etc.)."
        ),
    },
}

EXPANDED_GROUP_ALIASES: dict[str, list[str]] = {
    "btc-posicoes-abertas": ["btc_posicoes_abertas"],
    "derivativos-agro": ["derivativos_agro"],
    "indices-carteiras": ["indices_carteiras"],
}

ALL_GROUPS = {**GROUPS, **EXPANDED_GROUPS}
ALL_GROUP_ALIASES = {**GROUP_ALIASES, **EXPANDED_GROUP_ALIASES}


def list_datasets(group: str | None = None) -> list[dict[str, Any]]:
    """List the available B3 dataset partitions.

    Args:
        group: Optional group name (e.g. ``cotacaohistorica``,
            ``btc_posicoes_abertas``, ``derivativos_agro``,
            ``indices_carteiras``).

    Returns:
        Entries for the requested group.

    Raises:
        ValueError: If an unknown group is requested.
    """
    if group is not None:
        canonical_group = (
            EXPANDED_GROUP_ALIASES.get(group, [group])[0]
            if group in EXPANDED_GROUP_ALIASES
            else group
        )
        if canonical_group not in ALL_GROUPS:
            raise ValueError(f"Grupo desconhecido: {group!r}")
    else:
        canonical_group = DATASET_ID

    current_year = dt.date.today().year

    if canonical_group == DATASET_ID:
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

    if canonical_group == "btc_posicoes_abertas":
        return [
            {
                "id": f"btc_posicoes_abertas-{current_year}",
                "group": "btc_posicoes_abertas",
                "year": current_year,
                "dataset_id": "btc_posicoes_abertas",
                "ext": "csv",
            }
        ]

    if canonical_group == "derivativos_agro":
        contratos = ["BGI", "CCM", "ICF", "SJC"]
        return [
            {
                "id": f"derivativos_agro-{contrato}-{current_year}",
                "group": "derivativos_agro",
                "contrato": contrato,
                "year": current_year,
                "dataset_id": "derivativos_agro",
                "ext": "csv",
            }
            for contrato in contratos
        ]

    if canonical_group == "indices_carteiras":
        indices = ["IBOV", "IBRX100", "SMLL", "IDIV", "IFIX", "IFIL"]
        return [
            {
                "id": f"indices_carteiras-{indice}-{current_year}",
                "group": "indices_carteiras",
                "indice": indice,
                "year": current_year,
                "dataset_id": "indices_carteiras",
                "ext": "json",
            }
            for indice in indices
        ]

    raise ValueError(f"Grupo desconhecido: {group!r}")
