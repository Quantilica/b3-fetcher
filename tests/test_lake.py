"""Tests for Hive lake conversion of B3 COTAHIST data."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

from quantilica.analytics.lake import check_dataset, scan_dataset  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from b3_fetcher.constants import DATASET_ID  # noqa: E402
from b3_fetcher.lake import (  # noqa: E402
    SOURCE_ID,
    converter,
    year_from_path,
)
from b3_fetcher.plugin import app  # noqa: E402

FIXTURE_TXT = Path(__file__).parent / "fixtures" / "COTAHIST_D02012024.txt"


def test_entry_point_registered() -> None:
    eps = entry_points(group="quantilica.lake")
    matches = [ep for ep in eps if ep.name == "b3"]
    assert len(matches) == 1
    loaded = matches[0].load()
    assert loaded is converter
    assert loaded.source_id == SOURCE_ID


def test_year_from_path() -> None:
    assert year_from_path(Path("COTAHIST_A2024.zip")) == "2024"
    assert year_from_path(Path("COTAHIST_A2020@20261021.zip")) == "2020"
    assert year_from_path(Path("COTAHIST_D02012024.txt")) == "2024"
    assert year_from_path(Path("unknown.zip")) is None


def test_converter_datasets() -> None:
    assert converter.datasets() == [DATASET_ID]


def test_convert_end_to_end(tmp_path: Path) -> None:
    if not FIXTURE_TXT.exists():
        pytest.skip("Fixture COTAHIST_D02012024.txt não encontrada")

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    txt_path = raw_dir / "COTAHIST_A2024@20241021.txt"
    txt_path.write_bytes(FIXTURE_TXT.read_bytes())

    lake_dir = tmp_path / "lake"
    res = converter.convert(raw_dir, lake_dir)
    assert not res.errors, res.errors
    assert res.converted == 1
    assert res.skipped == 0

    dataset_dir = lake_dir / SOURCE_ID / DATASET_ID
    assert check_dataset(dataset_dir) == []

    df = scan_dataset(dataset_dir).collect()
    assert df.height == 6
    assert "ano" in df.columns
    assert df["ano"][0] == "2024"
    assert "simbolo" in df.columns
    assert "preco_ultimo_negocio" in df.columns

    # Second run skips
    res2 = converter.convert(raw_dir, lake_dir)
    assert not res2.errors
    assert res2.converted == 0
    assert res2.skipped == 1


def test_cli_convert(tmp_path: Path) -> None:
    if not FIXTURE_TXT.exists():
        pytest.skip("Fixture COTAHIST_D02012024.txt não encontrada")

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    txt_path = raw_dir / "COTAHIST_A2024@20241021.txt"
    txt_path.write_bytes(FIXTURE_TXT.read_bytes())

    lake_dir = tmp_path / "lake"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["convert", "-i", str(raw_dir), "--lake", str(lake_dir)],
    )
    assert result.exit_code == 0, result.output
    assert (lake_dir / SOURCE_ID / DATASET_ID).exists()
