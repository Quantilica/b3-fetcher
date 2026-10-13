"""Tests for the COTAHIST fixed-width reader (requires the `analysis` extra)."""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

import polars as pl
import pytest

from b3_fetcher.reader import (
    LINE_LENGTH,
    read_dimension,
    read_records,
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
    assert schema["preco_ultimo_negocio"] == pl.Float64
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
    assert row["preco_abertura"] == pytest.approx(10.20)
    assert row["preco_maximo"] == pytest.approx(10.36)
    assert row["preco_minimo"] == pytest.approx(8.50)
    assert row["preco_ultimo_negocio"] == pytest.approx(8.50)
    assert row["quantidade_negocios"] == 1993
    assert row["quantidade_titulos_negociados"] == 430400
    assert row["volume_negociado"] == pytest.approx(4014875.00)
    assert row["data_vencimento"] == dt.date(9999, 12, 31)
    assert row["codisi"] == "BRAALRACNOR6"
    assert row["dismes"] == 102


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
