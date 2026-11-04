"""Tests for the B3 COTAHIST dataset catalog."""

from __future__ import annotations

import base64
import datetime as dt
import json

import pytest

from b3_fetcher.catalog import ALL_GROUPS, GROUP_ALIASES, GROUPS, list_datasets
from b3_fetcher.constants import DATASET_ID, MIN_YEAR


def test_groups_expose_single_dataset():
    assert list(GROUPS) == [DATASET_ID]
    assert GROUP_ALIASES == {}


def test_all_groups_have_no_btc_without_source():
    assert list(ALL_GROUPS) == [DATASET_ID, "derivativos_agro", "indices_carteiras"]
    with pytest.raises(ValueError, match="Grupo desconhecido"):
        list_datasets("btc_posicoes_abertas")


def test_derivativos_agro_entries_use_requestname_for_business_days():
    entries = list_datasets("derivativos-agro", today=dt.date(2026, 11, 3))
    assert [e["date"] for e in entries] == [
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-11-02",
        "2026-11-03",
    ]
    first = entries[0]
    assert first["id"] == "derivativos_agro-2026-10-28"
    assert first["protocol"] == "requestname"
    assert first["url"] == (
        "https://arquivos.b3.com.br/api/download/requestname"
        "?fileName=DerivativesOpenPosition&date=2026-10-28"
    )


def test_derivativos_agro_lookback_from_env(monkeypatch):
    monkeypatch.setenv("B3_LOOKBACK_DAYS", "2")
    assert len(list_datasets("derivativos_agro", today=dt.date(2026, 11, 3))) == 2


def test_indices_carteiras_entries_cover_six_indices():
    entries = list_datasets("indices_carteiras", today=dt.date(2026, 11, 3))
    assert [e["indice"] for e in entries] == [
        "IBOV",
        "IBRX100",
        "SMLL",
        "IDIV",
        "IFIX",
        "IFIL",
    ]
    assert all(e["protocol"] == "portfolio" and e["ext"] == "json" for e in entries)
    # IBrX 100 usa o código IBXX na API
    ibrx = next(e for e in entries if e["indice"] == "IBRX100")
    payload = base64.b64decode(ibrx["url"].rsplit("/", 1)[1])
    assert json.loads(payload) == {"index": "IBXX", "language": "pt-br"}


def test_list_datasets_covers_full_history():
    current_year = dt.date.today().year
    entries = list_datasets()

    assert len(entries) == current_year - MIN_YEAR + 1
    assert entries[0]["year"] == MIN_YEAR
    assert entries[-1]["year"] == current_year


def test_list_datasets_entry_schema():
    entry = list_datasets()[0]

    assert entry["group"] == DATASET_ID
    assert entry["id"] == f"{DATASET_ID}-{MIN_YEAR}"
    assert entry["url"].endswith(f"/COTAHIST_A{MIN_YEAR}.zip")
    assert entry["ext"] == "zip"


def test_list_datasets_accepts_its_own_group():
    assert list_datasets(DATASET_ID) == list_datasets()


def test_list_datasets_rejects_unknown_group():
    with pytest.raises(ValueError, match="Grupo desconhecido"):
        list_datasets("outro")
