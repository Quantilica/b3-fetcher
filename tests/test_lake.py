"""Tests for Hive lake conversion of B3 COTAHIST data."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

import polars as pl  # noqa: E402
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
    assert converter.datasets() == [
        DATASET_ID,
        "btc_posicoes_abertas",
        "derivativos_agro",
        "indices_carteiras",
    ]


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
    assert df["ano"][0] == 2024
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


def test_btc_posicoes_abertas_lake_conversion(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "btc_posicoes_abertas"
    raw_dir.mkdir(parents=True)
    csv_file = raw_dir / "btc_posicoes_abertas_2024-10-29.csv"
    csv_file.write_text(
        "data_referencia;simbolo;codigo_isin;cnpj_emissor;quantidade;valor;taxa_media\n"
        "2024-10-29;PETR4;0BR123456789;01234567000199;100000;3500000.00;1.25\n"
        "2024-10-29;VALE3;BRVALEACNOR0;33592510000154;50000;3200000.00;0.85\n",
        encoding="utf-8",
    )

    lake_dir = tmp_path / "lake"
    res = converter.convert(raw_dir.parent, lake_dir, datasets=["btc_posicoes_abertas"])
    assert not res.errors, res.errors
    assert res.converted == 1

    dataset_dir = lake_dir / SOURCE_ID / "btc_posicoes_abertas"
    assert dataset_dir.exists()
    assert check_dataset(dataset_dir) == []

    df = scan_dataset(dataset_dir).collect()
    assert df.height == 2
    assert "ano" in df.columns
    assert df["ano"][0] == 2024
    assert df.schema["codigo_isin"] == pl.String
    assert df.schema["cnpj_emissor"] == pl.String
    assert df["codigo_isin"][0] == "0BR123456789"
    assert df["cnpj_emissor"][0] == "01234567000199"


def test_indices_carteiras_lake_conversion(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "indices_carteiras"
    raw_dir.mkdir(parents=True)
    json_file = raw_dir / "carteira_IBOV_2024-10-29.json"
    json_file.write_text(
        '[{"ticker": "PETR4", "codigo_isin": "0BRPETR", "peso": 8.5},'
        ' {"ticker": "VALE3", "codigo_isin": "BRVALE", "peso": 12.0}]',
        encoding="utf-8",
    )

    lake_dir = tmp_path / "lake"
    res = converter.convert(raw_dir.parent, lake_dir, datasets=["indices_carteiras"])
    assert not res.errors, res.errors
    assert res.converted == 1

    dataset_dir = lake_dir / SOURCE_ID / "indices_carteiras"
    assert dataset_dir.exists()
    assert check_dataset(dataset_dir) == []

    df = scan_dataset(dataset_dir).collect()
    assert df.height == 2
    assert df["indice"][0] == "IBOV"
    assert df.schema["codigo_isin"] == pl.String
    assert df["codigo_isin"][0] == "0BRPETR"


def test_derivativos_agro_lake_conversion(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "derivativos_agro"
    raw_dir.mkdir(parents=True)
    csv_file = raw_dir / "derivativos_agro_BGI_2024-10-29.csv"
    csv_file.write_text(
        "data_pregao;contrato;ticker;quantidade_aberta;valor_ajuste\n"
        "2024-10-29;BGI;BGIX24;1500;310.50\n",
        encoding="utf-8",
    )

    lake_dir = tmp_path / "lake"
    res = converter.convert(raw_dir.parent, lake_dir, datasets=["derivativos_agro"])
    assert not res.errors, res.errors
    assert res.converted == 1

    dataset_dir = lake_dir / SOURCE_ID / "derivativos_agro"
    assert dataset_dir.exists()
    assert check_dataset(dataset_dir) == []

    df = scan_dataset(dataset_dir).collect()
    assert df.height == 1
    assert "ano" in df.columns
    assert df["ano"][0] == 2024
    assert df.schema["ticker"] == pl.String
    assert df.schema["contrato"] == pl.String
    assert df["contrato"][0] == "BGI"


def test_convert_unknown_dataset(tmp_path: Path) -> None:
    res = converter.convert(tmp_path, tmp_path, datasets=["desconhecido_xyz"])
    assert len(res.errors) == 1
    assert "dataset desconhecido: desconhecido_xyz" in res.errors[0]


def test_inventory_b3(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "btc_2024-10-29.csv").write_text("a;b\n1;2\n")
    (raw_dir / "COTAHIST_A2024.zip").write_text("dummy")
    (raw_dir / "other.pdf").write_text("dummy")

    planned = converter.inventory(raw_dir)
    assert len(planned) == 3
    datasets = {p.path.name: (p.dataset, p.skip_reason) for p in planned}
    assert datasets["btc_2024-10-29.csv"] == ("btc_posicoes_abertas", None)
    assert datasets["COTAHIST_A2024.zip"] == (DATASET_ID, None)
    assert datasets["other.pdf"] == (None, "nao_tabular")
