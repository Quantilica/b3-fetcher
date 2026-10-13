"""Tests for the B3 COTAHIST dataset catalog."""

from __future__ import annotations

import datetime as dt

import pytest

from b3_fetcher.catalog import GROUP_ALIASES, GROUPS, list_datasets
from b3_fetcher.constants import DATASET_ID, MIN_YEAR


def test_groups_expose_single_dataset():
    assert list(GROUPS) == [DATASET_ID]
    assert GROUP_ALIASES == {}


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
