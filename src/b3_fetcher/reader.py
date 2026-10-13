"""Parsing of B3 COTAHIST fixed-width archives.

The COTAHIST file is a Latin-1 text where every line is exactly 245 bytes.
Each line starts with a two-digit record type (``00`` header, ``01`` quotation,
``99`` trailer). This module parses the ``01`` records into a Polars DataFrame
using the positional layout shipped in ``auxiliary_tables/registro01.csv``.

Requires the ``analysis`` extra (``polars``).
"""

from __future__ import annotations

import csv
import zipfile
from importlib import resources
from pathlib import Path
from typing import Any

import polars as pl

from .constants import AUXILIARY_TABLES_DIR

RECORD_TYPE_DETAIL = "01"
RECORD_TYPE_HEADER = "00"
RECORD_TYPE_TRAILER = "99"
LINE_LENGTH = 245
ENCODING = "latin-1"

_DATE_FIELDS = frozenset({"DATA", "DATVEN"})

# Campos com vírgula implícita: por padrão 2 casas decimais (preços/volume);
# ``preco_exercicio_pontos`` (PTOEXE) usa 6 conforme o layout da B3.
_DECIMAL_PLACES: dict[str, int] = {"preco_exercicio_pontos": 6}
_DEFAULT_DECIMALS = 2

_DIMENSION_RENAMES: dict[str, dict[str, str]] = {
    "codbdi": {"CODBDI": "bdi_id", "DESCRIÇÃO": "bdi"},
    "especi": {"ESPECI": "especificacao_id", "DESCRIÇÃO": "especificacao"},
    "indopc": {
        "INDOPC": "indice_correcao_id",
        "SÍMBOLO": "simbolo",
        "DESCRIÇÃO": "indice_correcao",
    },
    "tpmerc": {"TPMERC": "tipo_mercado_id", "DESCRIÇÃO": "tipo_mercado"},
}


def _auxiliary_path(filename: str) -> Any:
    """Return a Traversable for an auxiliary table inside the package."""
    return resources.files(__package__).joinpath(AUXILIARY_TABLES_DIR, filename)


def _read_auxiliary_csv(filename: str) -> list[dict[str, str]]:
    """Read an auxiliary layout/dimension CSV into a list of row dicts."""
    with _auxiliary_path(filename).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _classify(tipo: str) -> str:
    """Classify a layout field type into ``text``, ``int`` or ``decimal``.

    Args:
        tipo: The ``TIPO E TAMANHO`` cell (e.g. ``X(12)``, ``N(05)``,
            ``(11)V99``). A ``V`` marks a field with implied decimal places.

    Returns:
        One of ``text``, ``int`` or ``decimal``.
    """
    value = tipo.strip()
    if "V" in value:
        return "decimal"
    if value[:1] in {"N", "9"}:
        return "int"
    return "text"


def _layout() -> list[dict[str, Any]]:
    """Return the ordered ``01`` record layout as field descriptors."""
    fields: list[dict[str, Any]] = []
    for row in _read_auxiliary_csv("registro01.csv"):
        normalized = row["nome_normalizado"].strip()
        kind = _classify(row["TIPO E TAMANHO"])
        decimals = (
            _DECIMAL_PLACES.get(normalized, _DEFAULT_DECIMALS)
            if kind == "decimal"
            else 0
        )
        fields.append(
            {
                "raw_name": row["NOME DO CAMPO"].strip(),
                "normalized": normalized,
                "start": int(row["POS. INIC."]),
                "end": int(row["POS. FINAL"]),
                "kind": kind,
                "decimals": decimals,
            }
        )
    return fields


def _field_expr(field: dict[str, Any]) -> pl.Expr:
    """Build the Polars expression that extracts and casts one field."""
    start = field["start"] - 1
    length = field["end"] - field["start"] + 1
    raw = pl.col("__raw").str.slice(start, length)
    name = field["normalized"]

    if field["raw_name"] in _DATE_FIELDS:
        return raw.str.strip_chars().str.to_date("%Y%m%d", strict=False).alias(name)
    if field["kind"] == "text":
        collapsed = raw.str.replace_all(r"\s+", " ")
        return collapsed.str.strip_chars().alias(name)
    if field["kind"] == "int":
        return raw.str.strip_chars().cast(pl.Int64, strict=False).alias(name)
    if field["kind"] == "decimal":
        scaled = raw.str.strip_chars().cast(pl.Int64, strict=False).cast(pl.Float64)
        return (scaled / 10 ** field["decimals"]).alias(name)
    return raw.alias(name)


def _read_lines(filepath: Path) -> list[str]:
    """Read the COTAHIST lines from a ``.zip`` or ``.txt`` file (Latin-1)."""
    path = Path(filepath)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = [
                info.filename for info in archive.infolist() if not info.is_dir()
            ]
            if not members:
                raise ValueError(f"Nenhum arquivo encontrado em {path}")
            # Arquivos recentes usam extensão .TXT; os antigos trazem um único
            # membro sem extensão (ex.: COTAHIST.A1986).
            txt = [name for name in members if name.lower().endswith(".txt")]
            return (
                archive.read(txt[0] if txt else members[0])
                .decode(ENCODING)
                .splitlines()
            )
    return path.read_text(encoding=ENCODING).splitlines()


def read_records(filepath: Path) -> pl.DataFrame:
    """Parse the ``01`` (quotation) records of a COTAHIST archive.

    Args:
        filepath: Path to a downloaded ``.zip`` or extracted ``.txt``.

    Returns:
        A Polars DataFrame with one row per quotation record, columns named
        per the normalized layout (``data``, ``simbolo``, ``preco_*``, ...).
    """
    lines = _read_lines(filepath)
    detail = [line for line in lines if line[:2] == RECORD_TYPE_DETAIL]
    if not detail:
        return pl.DataFrame()
    raw = pl.DataFrame({"__raw": detail}, schema={"__raw": pl.Utf8})
    return raw.select(_field_expr(field) for field in _layout())


def read_dimension(name: str) -> pl.DataFrame:
    """Read a COTAHIST dimension table with normalized column names.

    Args:
        name: One of ``codbdi``, ``especi``, ``indopc`` or ``tpmerc``.

    Returns:
        A Polars DataFrame with the table's canonical column names.

    Raises:
        ValueError: If ``name`` is not a known dimension table.
    """
    if name not in _DIMENSION_RENAMES:
        raise ValueError(f"Tabela auxiliar desconhecida: {name!r}")
    with resources.as_file(_auxiliary_path(f"{name}.csv")) as path:
        df = pl.read_csv(path)
    return df.rename(_DIMENSION_RENAMES[name])
