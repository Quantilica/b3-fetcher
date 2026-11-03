"""Tests for the B3 COTAHIST data repository layout."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from b3_fetcher.storage import DataRepository


def test_path_for_entry_partitions_by_year(tmp_path: Path):
    entry = {"group": "cotacaohistorica", "year": 2024, "ext": "zip"}
    path = DataRepository(tmp_path).path_for_entry(
        entry, last_modified=dt.date(2024, 1, 2)
    )

    assert path == (
        tmp_path / "cotacaohistorica" / "2024" / "cotacaohistorica_2024@20240102.zip"
    )


def test_path_for_entry_without_timestamp(tmp_path: Path):
    """When last_modified is not provided (defaults to None), fallback to today's date."""
    from datetime import date

    today = date.today()
    today_str = today.strftime("%Y%m%d")

    path = DataRepository(tmp_path).path_for_entry({"year": 1999, "ext": "zip"})

    assert path.name == f"cotacaohistorica_1999@{today_str}.zip"
    assert path.parent.name == "1999"


def test_path_for_entry_fallback_timestamp(tmp_path: Path):
    """When last_modified is None, filename should get today's @YYYYMMDD stamp."""
    from datetime import date

    today = date.today()
    today_str = today.strftime("%Y%m%d")

    path = DataRepository(tmp_path).path_for_entry(
        {"year": 2025, "ext": "zip"}, last_modified=None
    )

    assert f"cotacaohistorica_2025@{today_str}.zip" == path.name
    assert path.parent.name == "2025"
