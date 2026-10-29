"""Parsing of B3 COTAHIST fixed-width archives.

The COTAHIST file is a Latin-1 text where every line is exactly 245 bytes.
Each line starts with a two-digit record type (``00`` header, ``01`` quotation,
``99`` trailer). This module parses the ``01`` records into a Polars DataFrame
using the positional layout shipped in ``auxiliary_tables/registro01.csv``.

Requires the ``analysis`` extra (``polars``).
"""

from __future__ import annotations

import csv
import re
import zipfile
from importlib import resources
from pathlib import Path
from typing import Any

try:
    import polars as pl
    from quantilica.analytics.writer import to_parquet
except ImportError as exc:
    raise ImportError(
        "b3_fetcher.reader requer o extra 'analysis'. "
        "Instale com: uv add 'b3-fetcher[analysis]' "
        "--index https://index.quantilica.com/simple/"
    ) from exc

from .constants import AUXILIARY_TABLES_DIR

RECORD_TYPE_DETAIL = "01"
RECORD_TYPE_HEADER = "00"
RECORD_TYPE_TRAILER = "99"
LINE_LENGTH = 245
ENCODING = "latin-1"

_DATE_FIELDS = frozenset({"DATA", "DATVEN"})

# Campos com vírgula implícita trazem no layout o número de dígitos inteiros,
# como ``(11)V99`` (PREABE, 13 posições) ou ``(07)V06`` (PTOEXE, 13 posições):
# as casas decimais são as posições restantes do campo.
_INTEGER_DIGITS = re.compile(r"^\((\d+)\)V")

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
        tipo = row["TIPO E TAMANHO"].strip()
        kind = _classify(tipo)
        start = int(row["POS. INIC."])
        end = int(row["POS. FINAL"])
        length = end - start + 1
        decimals = 0
        if kind == "decimal":
            match = _INTEGER_DIGITS.match(tipo)
            if not match or int(match.group(1)) >= length:
                raise ValueError(f"Layout decimal inválido para {normalized}: {tipo}")
            decimals = length - int(match.group(1))
        fields.append(
            {
                "raw_name": row["NOME DO CAMPO"].strip(),
                "normalized": normalized,
                "start": start,
                "end": end,
                "length": length,
                "kind": kind,
                "decimals": decimals,
            }
        )
    return fields


def _blank_to_null(expr: pl.Expr) -> pl.Expr:
    """Strip a field and turn an all-blank field into null (never other values)."""
    stripped = expr.str.strip_chars()
    return pl.when(stripped == "").then(None).otherwise(stripped)


def _field_expr(field: dict[str, Any]) -> pl.Expr:
    """Build the Polars expression that extracts and casts one field.

    Conversions are strict: a blank field becomes null, and any other value
    that does not fit the layout type raises instead of becoming null.
    Fields with an implied decimal point become exact ``Decimal`` values
    (precision = field length, scale = decimal places), never floats.
    """
    start = field["start"] - 1
    raw = pl.col("__raw").str.slice(start, field["length"])
    name = field["normalized"]

    if field["raw_name"] in _DATE_FIELDS:
        return _blank_to_null(raw).str.to_date("%Y%m%d", strict=True).alias(name)
    if field["kind"] == "text":
        collapsed = raw.str.replace_all(r"\s+", " ")
        return collapsed.str.strip_chars().alias(name)
    if field["kind"] == "int":
        return _blank_to_null(raw).cast(pl.Int64, strict=True).alias(name)
    if field["kind"] == "decimal":
        decimals = field["decimals"]
        digits = _blank_to_null(raw).str.zfill(decimals + 1)
        text = pl.concat_str(
            [digits.str.head(-decimals), pl.lit("."), digits.str.tail(decimals)]
        )
        dtype = pl.Decimal(precision=field["length"], scale=decimals)
        return text.cast(dtype, strict=True).alias(name)
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
            return _decode_lines(archive.read(txt[0] if txt else members[0]))
    return _decode_lines(path.read_bytes())


def _decode_lines(data: bytes) -> list[str]:
    """Decode the records as Latin-1, except the ones written in UTF-8.

    A few records come in UTF-8 (``FROTA OCEÂNI`` in 2026): read as Latin-1, the
    two bytes of ``Â`` become two characters and every later field shifts by one
    (``DATVEN`` = ``09999123``). A record longer than the layout that decodes to
    the right length as UTF-8 is taken as UTF-8.
    """
    lines = []
    for raw in data.splitlines():
        line = raw.decode(ENCODING)
        if len(raw) > LINE_LENGTH:
            try:
                utf8 = raw.decode("utf-8")
            except UnicodeDecodeError:
                pass
            else:
                if len(utf8) == LINE_LENGTH:
                    line = utf8
        lines.append(line)
    return lines


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


def write_parquet(
    df: pl.DataFrame,
    target: Path,
    *,
    source_path: Path | None = None,
) -> Path:
    """Write a DataFrame as Parquet (zstd) with optional provenance.

    Delegates to the canonical ``to_parquet`` from ``quantilica.analytics.writer``
    (atomic write-temp-rename); when the raw source file has a
    ``.manifest.json`` sidecar, the ``quantilica.*`` metadata are injected
    into the Parquet and a provenance sidecar is written next to the target.

    Args:
        df: The DataFrame to write.
        target: Destination path of the Parquet file.
        source_path: Optional raw source file, used to inject the manifest
            sidecar metadata.

    Returns:
        Path: The path of the written Parquet file.
    """
    return to_parquet(df, target, source_path=source_path)
