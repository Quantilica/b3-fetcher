"""Tests for the COTAHIST fixed-width reader (requires the `analysis` extra)."""

from __future__ import annotations

import datetime as dt
import importlib
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from b3_fetcher.reader import (
    LINE_LENGTH,
    _layout,
    read_dimension,
    read_records,
    write_parquet,
)

FIXTURE = Path(__file__).parent / "fixtures" / "COTAHIST_D02012024.txt"


@pytest.fixture(scope="module")
def records() -> pl.DataFrame:
    return read_records(FIXTURE)


def test_fixture_lines_are_fixed_width():
    lines = FIXTURE.read_text(encoding="latin-1").splitlines()
    assert all(len(line) == LINE_LENGTH for line in lines)


def test_read_records_only_returns_detail_rows(records: pl.DataFrame):
    lines = FIXTURE.read_text(encoding="latin-1").splitlines()
    detail = [line for line in lines if line[:2] == "01"]
    assert records.height == len(detail) == 6


def test_read_records_schema(records: pl.DataFrame):
    schema = records.schema
    assert schema["data"] == pl.Date
    assert schema["data_vencimento"] == pl.Date
    assert schema["simbolo"] == pl.Utf8
    assert schema["preco_ultimo_negocio"] == pl.Decimal(precision=13, scale=2)
    assert schema["volume_negociado"] == pl.Decimal(precision=18, scale=2)
    assert schema["preco_exercicio_pontos"] == pl.Decimal(precision=13, scale=6)
    assert schema["quantidade_negocios"] == pl.Int64
    assert schema["quantidade_titulos_negociados"] == pl.Int64
    assert schema["indice_correcao_id"] == pl.Int64


def test_read_records_values_for_aalr3(records: pl.DataFrame):
    row = records.filter(pl.col("simbolo") == "AALR3").row(0, named=True)

    assert row["tipreg"] == 1
    assert row["data"] == dt.date(2024, 1, 2)
    assert row["bdi_id"] == "02"
    assert row["tipo_mercado_id"] == 10
    assert row["nome_resumido"] == "ALLIAR"
    assert row["especificacao_id"] == "ON NM"
    assert row["simbolo_moeda"] == "R$"
    assert row["preco_abertura"] == Decimal("10.20")
    assert row["preco_maximo"] == Decimal("10.36")
    assert row["preco_minimo"] == Decimal("8.50")
    assert row["preco_ultimo_negocio"] == Decimal("8.50")
    assert row["quantidade_negocios"] == 1993
    assert row["quantidade_titulos_negociados"] == 430400
    assert row["volume_negociado"] == Decimal("4014875.00")
    assert row["data_vencimento"] == dt.date(9999, 12, 31)
    assert row["codisi"] == "BRAALRACNOR6"
    assert row["dismes"] == 102


def _detail_line(**fields: str) -> str:
    """First ``01`` line of the fixture with some fields replaced (raw text)."""
    lines = FIXTURE.read_text(encoding="latin-1").splitlines()
    line = next(line for line in lines if line[:2] == "01")
    layout = {field["normalized"]: field for field in _layout()}
    for name, value in fields.items():
        field = layout[name]
        assert len(value) == field["length"], name
        line = line[: field["start"] - 1] + value + line[field["end"] :]
    assert len(line) == LINE_LENGTH
    return line


def _read_line(tmp_path: Path, line: str) -> pl.DataFrame:
    path = tmp_path / "one.txt"
    path.write_text(line + "\n", encoding="latin-1")
    return read_records(path)


def test_layout_derives_scale_from_implied_decimal_point():
    layout = {field["normalized"]: field for field in _layout()}
    # (11)V99 in 13 positions, (16)V99 in 18, (07)V06 in 13.
    assert (
        layout["preco_abertura"]["length"],
        layout["preco_abertura"]["decimals"],
    ) == (13, 2)
    assert (
        layout["volume_negociado"]["length"],
        layout["volume_negociado"]["decimals"],
    ) == (18, 2)
    assert (
        layout["preco_exercicio_pontos"]["length"],
        layout["preco_exercicio_pontos"]["decimals"],
    ) == (13, 6)


def test_implied_decimal_is_exact_not_float(tmp_path: Path):
    # 3780 in a (11)V99 field is R$ 37,80; as float it would read
    # 37.800000000000004 (seen with PETR4 on 2024-06-28).
    line = _detail_line(
        preco_abertura="0000000003780",
        volume_negociado="000000083621636600",
        preco_exercicio_pontos="0000001234567",
    )
    row = _read_line(tmp_path, line).row(0, named=True)
    assert row["preco_abertura"] == Decimal("37.80")
    assert str(row["preco_abertura"]) == "37.80"
    assert row["volume_negociado"] == Decimal("836216366.00")
    assert row["preco_exercicio_pontos"] == Decimal("1.234567")


def test_largest_values_fit_their_decimal_type(tmp_path: Path):
    line = _detail_line(
        preco_abertura="9" * 13,
        volume_negociado="9" * 18,
        quantidade_titulos_negociados="9" * 18,
    )
    row = _read_line(tmp_path, line).row(0, named=True)
    assert row["preco_abertura"] == Decimal("99999999999.99")
    assert row["volume_negociado"] == Decimal("9999999999999999.99")
    assert row["quantidade_titulos_negociados"] == 999_999_999_999_999_999


def test_blank_numeric_and_date_fields_become_null(tmp_path: Path):
    line = _detail_line(
        preco_abertura=" " * 13,
        quantidade_negocios=" " * 5,
        data_vencimento=" " * 8,
    )
    row = _read_line(tmp_path, line).row(0, named=True)
    assert row["preco_abertura"] is None
    assert row["quantidade_negocios"] is None
    assert row["data_vencimento"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preco_abertura", "00000000037X0"),
        ("quantidade_negocios", "01A93"),
        ("data_vencimento", "20241332"),
    ],
)
def test_invalid_values_raise_instead_of_becoming_null(tmp_path: Path, field, value):
    line = _detail_line(**{field: value})
    with pytest.raises(pl.exceptions.InvalidOperationError):
        _read_line(tmp_path, line)


def test_read_records_reads_zip(tmp_path: Path):
    archive = tmp_path / "COTAHIST_D02012024.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(FIXTURE, "COTAHIST_D02012024.TXT")

    assert read_records(archive).height == 6


def test_read_records_reads_zipless_member_without_txt_extension(tmp_path: Path):
    # Arquivos anuais antigos (ex.: 1986) trazem um membro sem extensão.
    archive = tmp_path / "COTAHIST_A1986.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(FIXTURE, "COTAHIST.A1986")

    assert read_records(archive).height == 6


def test_read_records_empty_when_no_detail(tmp_path: Path):
    only_header = tmp_path / "empty.txt"
    only_header.write_text("0" * LINE_LENGTH + "\n", encoding="latin-1")
    assert read_records(only_header).height == 0


def test_read_dimension_renames_columns():
    tpmerc = read_dimension("tpmerc")
    assert tpmerc.columns == ["tipo_mercado_id", "tipo_mercado"]
    assert tpmerc.filter(pl.col("tipo_mercado_id") == 10).item(0, "tipo_mercado") == (
        "VISTA"
    )


def test_read_dimension_rejects_unknown():
    with pytest.raises(ValueError, match="Tabela auxiliar desconhecida"):
        read_dimension("nao-existe")


def _manifest_for(raw: Path):
    from quantilica.core.manifests import DownloadManifest, write_manifest_sidecar

    manifest = DownloadManifest(
        source_id="b3",
        dataset_id="cotahist",
        url="https://example.org/cotahist.zip",
        fetched_at="2026-01-01T00:00:00Z",
        sha256="abc123",
        size_bytes=raw.stat().st_size,
        path=str(raw),
        producer="b3-fetcher",
    )
    write_manifest_sidecar(raw, manifest)


def test_write_parquet_with_provenance(tmp_path: Path):
    raw = tmp_path / "COTAHIST_D02012024.txt"
    raw.write_bytes(FIXTURE.read_bytes())
    _manifest_for(raw)

    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    target = tmp_path / "out" / "cotahist.parquet"

    result = write_parquet(df, target, source_path=raw)

    assert result == target
    assert target.exists()
    assert pl.read_parquet(target).shape == (2, 2)

    sidecar = tmp_path / "out" / "cotahist.parquet.manifest.json"
    assert sidecar.exists()
    assert (
        '"sha256": "abc123"' in sidecar.read_text() or "abc123" in sidecar.read_text()
    )

    import pyarrow.parquet as pq

    keys = {
        k.decode() if isinstance(k, bytes) else k: v.decode()
        if isinstance(v, bytes)
        else v
        for k, v in pq.read_metadata(target).metadata.items()
    }
    assert keys["quantilica.dataset_id"] == "cotahist"
    assert keys["quantilica.origin_sha256"] == "abc123"
    assert keys["quantilica.source_id"] == "b3"


def test_write_parquet_without_source_writes_no_sidecar(tmp_path: Path):
    df = pl.DataFrame({"a": [1, 2]})
    target = tmp_path / "plain.parquet"

    result = write_parquet(df, target)

    assert result.exists()
    assert not (tmp_path / "plain.parquet.manifest.json").exists()


def test_analysis_extra_mensagem_acionavel():
    saved_polars = sys.modules.get("polars")
    saved_analytics = sys.modules.get("quantilica.analytics.writer")
    try:
        sys.modules["quantilica.analytics.writer"] = None
        sys.modules.pop("b3_fetcher.reader", None)
        with pytest.raises(
            ImportError, match="b3_fetcher.reader requer o extra 'analysis'"
        ):
            importlib.import_module("b3_fetcher.reader")
    finally:
        sys.modules.pop("b3_fetcher.reader", None)
        if saved_analytics is not None:
            sys.modules["quantilica.analytics.writer"] = saved_analytics
        else:
            sys.modules.pop("quantilica.analytics.writer", None)
        if saved_polars is not None:
            sys.modules["polars"] = saved_polars
        else:
            sys.modules.pop("polars", None)
        importlib.import_module("b3_fetcher.reader")
