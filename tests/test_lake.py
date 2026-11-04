"""Tests for Hive lake conversion of B3 COTAHIST data."""

from __future__ import annotations

import datetime as dt
import shutil
from decimal import Decimal
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
    B3PathError,
    converter,
    resolve_b3_partitions,
    year_from_path,
)
from b3_fetcher.plugin import app  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_TXT = FIXTURES / "COTAHIST_D02012024.txt"


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


def _stage(tmp_path: Path, group: str, name: str, fixture: str) -> Path:
    raw = tmp_path / "raw"
    target = raw / group / "2026" / name
    target.parent.mkdir(parents=True)
    shutil.copy(FIXTURES / fixture, target)
    return raw


def test_indices_carteiras_lake_conversion(tmp_path: Path) -> None:
    raw = _stage(
        tmp_path,
        "indices_carteiras",
        "indices_carteiras-IBOV-2026-11-03.json",
        "indices_carteiras_IBOV_response.json",
    )
    lake_dir = tmp_path / "lake"
    res = converter.convert(raw, lake_dir, datasets=["indices_carteiras"])
    assert not res.errors, res.errors
    assert res.converted == 1

    dataset_dir = lake_dir / SOURCE_ID / "indices_carteiras"
    assert check_dataset(dataset_dir) == []
    assert (dataset_dir / "indice=IBOV" / "ano=2026" / "mes=11" / "dia=03").is_dir()

    df = scan_dataset(dataset_dir).collect()
    assert df.height == 12
    assert df["indice"][0] == "IBOV"
    assert df.schema["ticker"] == pl.String
    assert df["ticker"][0] == "ALOS3"
    assert df["participacao_pct"][0] == Decimal("0.479")
    assert df["qtd_teorica"][1] == 4043349180
    assert df["data_carteira"][0] == dt.date(2026, 11, 3)
    assert df["redutor"][0] == Decimal("13998953.64015646")

    again = converter.convert(raw, lake_dir, datasets=["indices_carteiras"])
    assert (again.converted, again.skipped, again.errors) == (0, 1, [])


def test_derivativos_agro_lake_conversion(tmp_path: Path) -> None:
    raw = _stage(
        tmp_path,
        "derivativos_agro",
        "derivativos_agro-2026-10-29.csv",
        "derivatives_open_position_20261029.csv",
    )
    lake_dir = tmp_path / "lake"
    res = converter.convert(raw, lake_dir, datasets=["derivativos_agro"])
    assert not res.errors, res.errors
    assert res.converted == 1

    dataset_dir = lake_dir / SOURCE_ID / "derivativos_agro"
    assert check_dataset(dataset_dir) == []
    base = dataset_dir / "ano=2026" / "mes=10" / "dia=29"
    assert sorted(p.name for p in base.iterdir()) == [
        "contrato=BGI",
        "contrato=CCM",
        "contrato=CNL",
        "contrato=ETH",
        "contrato=ICF",
        "contrato=SJC",
    ]

    df = scan_dataset(dataset_dir).collect()
    # 5 ativos-objeto x 3 linhas + CNL (1); as linhas de EQUITY/FINANCIAL ficam de fora.
    assert df.height == 16
    assert set(df["segmento"]) == {"AGRIBUSINESS"}
    assert df.schema["ticker"] == pl.String
    assert df.schema["codigo_isin"] == pl.String
    assert df.schema["contrato"] == pl.String
    bgi = df.filter(pl.col("ticker") == "BGIF27").row(0, named=True)
    assert bgi["contrato"] == "BGI"
    assert bgi["contratos_em_aberto"] == 6044
    assert bgi["variacao_contratos_em_aberto"] == 108
    assert (
        df.filter(pl.col("ticker") == "ICFH27")["variacao_contratos_em_aberto"][0]
        == -18
    )

    again = converter.convert(raw, lake_dir, datasets=["derivativos_agro"])
    assert (again.converted, again.skipped, again.errors) == (0, 1, [])


def test_manifest_sidecars_are_not_converted(tmp_path: Path) -> None:
    raw = _stage(
        tmp_path,
        "indices_carteiras",
        "indices_carteiras-IBOV-2026-11-03.json",
        "indices_carteiras_IBOV_response.json",
    )
    sidecar = next(raw.rglob("*.json")).with_name(
        "indices_carteiras-IBOV-2026-11-03.json.manifest.json"
    )
    sidecar.write_text('{"sha256": "x"}', encoding="utf-8")
    res = converter.convert(raw, tmp_path / "lake")
    assert (res.converted, res.errors) == (1, [])


def test_derivativos_agro_rejects_html_payload(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "derivativos_agro" / "2026"
    raw.mkdir(parents=True)
    (raw / "derivativos_agro-2026-10-29.csv").write_text(
        "<html><body>Manutencao</body></html>", encoding="utf-8"
    )
    res = converter.convert(tmp_path / "raw", tmp_path / "lake")
    assert res.converted == 0
    assert len(res.errors) == 1
    assert "derivativos_agro-2026-10-29.csv" in res.errors[0]


def test_partition_without_date_is_counted_error_not_default(tmp_path: Path) -> None:
    """Sem data no nome, nada de cair em 01/01 nem em hoje: erro contado."""
    raw = tmp_path / "raw" / "derivativos_agro"
    raw.mkdir(parents=True)
    shutil.copy(
        FIXTURES / "derivatives_open_position_20261029.csv",
        raw / "derivativos_agro.csv",
    )
    res = converter.convert(tmp_path / "raw", tmp_path / "lake")
    assert res.converted == 0
    assert len(res.errors) == 1
    assert "sem data" in res.errors[0]
    assert not (tmp_path / "lake" / SOURCE_ID / "derivativos_agro").exists()


def test_resolve_partitions_raises_without_date_or_index() -> None:
    with pytest.raises(B3PathError, match="sem data"):
        resolve_b3_partitions("derivativos_agro", Path("derivativos_agro.csv"))
    with pytest.raises(B3PathError, match="data inválida"):
        resolve_b3_partitions(
            "derivativos_agro", Path("derivativos_agro-2026-02-30.csv")
        )
    with pytest.raises(B3PathError, match="índice"):
        resolve_b3_partitions(
            "indices_carteiras", Path("indices_carteiras-XXXX-2026-11-03.json")
        )
    assert resolve_b3_partitions(
        "indices_carteiras", Path("indices_carteiras-IBRX100-2026-11-03.json")
    ) == {"indice": "IBRX100", "ano": "2026", "mes": "11", "dia": "03"}


def test_unrecognized_file_is_counted_error(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "mistério.csv").write_text("a;b\n1;2\n", encoding="utf-8")
    res = converter.convert(raw, tmp_path / "lake")
    assert len(res.errors) == 1
    assert "identificar o dataset" in res.errors[0]


def test_convert_unknown_dataset(tmp_path: Path) -> None:
    res = converter.convert(tmp_path, tmp_path, datasets=["desconhecido_xyz"])
    assert len(res.errors) == 1
    assert "dataset desconhecido: desconhecido_xyz" in res.errors[0]


def test_inventory_b3(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "derivativos_agro-2024-10-29.csv").write_text("a;b\n1;2\n")
    (raw_dir / "COTAHIST_A2024.zip").write_text("dummy")
    (raw_dir / "other.pdf").write_text("dummy")

    planned = converter.inventory(raw_dir)
    assert len(planned) == 3
    datasets = {p.path.name: (p.dataset, p.skip_reason) for p in planned}
    assert datasets["derivativos_agro-2024-10-29.csv"] == ("derivativos_agro", None)
    assert datasets["COTAHIST_A2024.zip"] == (DATASET_ID, None)
    assert datasets["other.pdf"] == (None, "nao_tabular")
