"""Convert raw B3 COTAHIST archives into the Hive-partitioned lake.

Each raw annual ZIP/TXT lands in
``<lake>/b3/cotacaohistorica/ano=<ano>/<file_key>.parquet``.
Quotation records (01) are parsed, typed with exact decimals, dates and integers,
and stored in Parquet format.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import polars as pl
    from quantilica.analytics.lake import LakeError, LakeWriter
    from quantilica.core.lake import DatasetDescriptor, partition_types_for
except ImportError as exc:
    raise ImportError(
        "b3_fetcher.lake requer o extra 'analysis': "
        "uv add 'b3-fetcher[analysis]' "
        "--index https://index.quantilica.com/simple/"
    ) from exc

from b3_fetcher import __version__
from b3_fetcher.constants import DATASET_ID
from b3_fetcher.reader import read_records

SOURCE_ID = "b3"
PARTITION_KEYS = ["ano"]
PARTITION_TYPES = partition_types_for(PARTITION_KEYS)

DATASET_SPECS = {
    DATASET_ID: {
        "alias": "cotahist",
        "partition_keys": ["ano"],
        "partition_types": partition_types_for(["ano"]),
    },
    "btc_posicoes_abertas": {
        "alias": "btc_posicoes_abertas",
        "partition_keys": ["ano", "mes", "dia"],
        "partition_types": partition_types_for(["ano", "mes", "dia"]),
    },
    "derivativos_agro": {
        "alias": "derivativos_agro",
        "partition_keys": ["ano", "mes", "dia"],
        "partition_types": partition_types_for(["ano", "mes", "dia"]),
    },
    "indices_carteiras": {
        "alias": "indices_carteiras",
        "partition_keys": ["indice", "ano", "mes", "dia"],
        "partition_types": partition_types_for(["indice", "ano", "mes", "dia"]),
    },
}

DATASET_ALIASES = {
    "cotahist": DATASET_ID,
    "btc-posicoes-abertas": "btc_posicoes_abertas",
    "derivativos-agro": "derivativos_agro",
    "indices-carteiras": "indices_carteiras",
}

_ANNUAL = re.compile(r"_A(?P<year>\d{4})", re.IGNORECASE)
_DAILY = re.compile(r"_D\d{4}(?P<year>\d{4})", re.IGNORECASE)
_YEAR = re.compile(r"(?:^|[-_@])(?P<year>(?:19|20)\d{2})(?:[-_@.]|$)")
_YMD = re.compile(
    r"(?:^|[-_@])(?P<ano>(?:19|20)\d{2})[-_]?(?P<mes>0[1-9]|1[0-2])[-_]?(?P<dia>0[1-9]|[12]\d|3[01])(?:[-_@.]|$)"
)


@dataclass
class ConvertResult:
    """Counts of a conversion run; ``errors`` holds one message per failure."""

    converted: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def year_from_path(path: Path) -> str | None:
    """Extract 4-digit year from COTAHIST filename."""
    name = path.name
    m_ann = _ANNUAL.search(name)
    if m_ann:
        return m_ann["year"]
    m_day = _DAILY.search(name)
    if m_day:
        return m_day["year"]
    m_yr = _YEAR.search(name)
    if m_yr:
        return m_yr["year"]
    return None


def resolve_b3_dataset(path: Path) -> str:
    """Resolve the dataset ID from path."""
    path_str = f"{path.parent.name}/{path.name}".lower()
    if "btc" in path_str:
        return "btc_posicoes_abertas"
    if "derivativo" in path_str or "derivatives" in path_str:
        return "derivativos_agro"
    if "indice" in path_str or "index" in path_str or "portfolio" in path_str:
        return "indices_carteiras"
    return DATASET_ID


def resolve_b3_partitions(dataset_id: str, path: Path) -> dict[str, str]:
    """Resolve partition values from path."""
    name = path.name
    parent = path.parent.name
    search_str = f"{parent}_{name}"

    if dataset_id == DATASET_ID:
        yr = year_from_path(path)
        return {"ano": yr} if yr else {}

    m_ymd = _YMD.search(search_str)
    ano = m_ymd["ano"] if m_ymd else str(dt.date.today().year)
    mes = m_ymd["mes"] if m_ymd else "01"
    dia = m_ymd["dia"] if m_ymd else "01"

    if dataset_id == "indices_carteiras":
        indice = "IBOV"
        for candidate in ("IBOV", "IBRX100", "SMLL", "IDIV", "IFIX", "IFIL"):
            if candidate.lower() in search_str.lower():
                indice = candidate
                break
        return {"indice": indice, "ano": ano, "mes": mes, "dia": dia}

    return {"ano": ano, "mes": mes, "dia": dia}


def _detect_code_overrides(path: Path) -> dict[str, Any]:
    """Detecta colunas de código pelo cabeçalho para leitura direta como pl.String."""
    try:
        with open(path, "rb") as f:
            line = f.readline().decode("latin-1", errors="replace").strip()
        sep = ";" if ";" in line else ","
        headers = [h.strip('" ') for h in line.split(sep)]
        overrides: dict[str, Any] = {}
        for h in headers:
            norm = h.lower().replace("-", "_")
            if any(
                k in norm
                for k in (
                    "isin",
                    "ticker",
                    "simbolo",
                    "cnpj",
                    "codigo_cvm",
                    "cd_cvm",
                    "contrato",
                    "indice",
                )
            ):
                overrides[h] = pl.String
        return overrides
    except Exception:
        return {}


def _cast_b3_codes(df: pl.DataFrame) -> pl.DataFrame:
    """Garante que códigos B3 (ISIN, ticker, CNPJ, código CVM) sejam pl.String."""
    exprs = []
    for col in df.columns:
        norm = col.lower().replace("-", "_")
        if any(
            k in norm
            for k in (
                "isin",
                "ticker",
                "simbolo",
                "cnpj",
                "codigo_cvm",
                "cd_cvm",
                "contrato",
                "indice",
            )
        ):
            if df.schema[col] != pl.String:
                exprs.append(pl.col(col).cast(pl.String))
    return df.with_columns(exprs) if exprs else df


class LakeConverter:
    """Converter registered under the ``quantilica.lake`` entry point."""

    source_id = SOURCE_ID

    def datasets(self) -> list[str]:
        """Dataset ids this converter writes to the lake."""
        return list(DATASET_SPECS)

    def all_datasets(self) -> list[str]:
        """All dataset ids supported by this converter."""
        return list(DATASET_SPECS)

    def convert(
        self,
        input_dir: Path,
        lake_dir: Path,
        *,
        datasets: list[str] | None = None,
        force: bool = False,
    ) -> ConvertResult:
        """Convert raw B3 files into ``lake_dir``.

        Args:
            input_dir: Root directory containing raw files.
            lake_dir: Root of the lake.
            datasets: Optional list of dataset ids to convert; None converts all.
            force: Reconvert even if sha256 already matches in the lake.

        Returns:
            ConvertResult: Files converted, skipped, and error messages.
        """
        input_dir = Path(input_dir)
        lake_dir = Path(lake_dir)
        result = ConvertResult()
        if not input_dir.is_dir():
            result.errors.append(f"diretório '{input_dir}' não existe")
            return result

        requested_canonical: set[str] | None = None
        if datasets:
            requested_canonical = set()
            unknown = set()
            for d in datasets:
                canonical = DATASET_ALIASES.get(d, d)
                if canonical in DATASET_SPECS:
                    requested_canonical.add(canonical)
                else:
                    unknown.add(d)
            if unknown:
                for u in sorted(unknown):
                    result.errors.append(f"dataset desconhecido: {u}")
                return result

        files = sorted(
            p
            for p in input_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".zip", ".txt", ".csv", ".json"}
        )

        writers: dict[str, LakeWriter] = {}

        for path in files:
            ds_id = resolve_b3_dataset(path)
            if requested_canonical and ds_id not in requested_canonical:
                continue

            spec = DATASET_SPECS[ds_id]
            partitions = resolve_b3_partitions(ds_id, path)

            if ds_id == DATASET_ID and "ano" not in partitions:
                result.errors.append(
                    f"{path.name}: não foi possível inferir o ano da partição"
                )
                continue

            if ds_id not in writers:
                writers[ds_id] = LakeWriter(
                    lake_dir / SOURCE_ID / ds_id,
                    DatasetDescriptor(
                        source_id=SOURCE_ID,
                        dataset_id=ds_id,
                        alias=spec["alias"],
                        partition_keys=spec["partition_keys"],
                        partition_types=spec["partition_types"],
                    ),
                    force=force,
                )
            writer = writers[ds_id]

            try:
                if ds_id == DATASET_ID:
                    df = read_records(path)
                elif path.suffix.lower() in {".csv", ".txt"}:
                    overrides = _detect_code_overrides(path)
                    try:
                        df = pl.read_csv(
                            path,
                            separator=";",
                            schema_overrides=overrides,
                            infer_schema_length=1000,
                        )
                    except Exception:
                        df = pl.read_csv(
                            path,
                            separator=",",
                            schema_overrides=overrides,
                            infer_schema_length=1000,
                        )
                elif path.suffix.lower() == ".json":
                    df = pl.read_json(path)
                else:
                    df = read_records(path)

                df = _cast_b3_codes(df)

                part_keys_lower = {k.lower() for k in partitions.keys()}
                norm_df = df.drop(
                    [c for c in df.columns if c.lower() in part_keys_lower]
                )

                written = writer.write_polars(
                    norm_df,
                    path,
                    partitions=partitions,
                    converter=f"b3-fetcher {__version__}",
                )
            except (
                LakeError,
                OSError,
                pl.exceptions.PolarsError,
                Exception,
            ) as exc:
                message = str(exc).strip()
                first_line = message.splitlines()[0] if message else repr(exc)
                result.errors.append(f"{path.name}: {first_line}")
                continue

            if written.status == "skipped":
                result.skipped += 1
            else:
                result.converted += 1

        return result

    def inventory(self, input_dir: Path) -> list[Any]:
        """Return planned datasets for each raw file."""
        from quantilica.core.lake import Planned

        input_dir = Path(input_dir)
        if not input_dir.is_dir():
            return []

        planned: list[Planned] = []
        for path in sorted(input_dir.rglob("*")):
            if not path.is_file() or path.name.endswith((".manifest.json", ".tmp")):
                continue
            if path.suffix.lower() in {".zip", ".txt", ".csv", ".json"}:
                ds_id = resolve_b3_dataset(path)
                planned.append(Planned(path, dataset=ds_id))
            else:
                planned.append(Planned(path, skip_reason="nao_tabular"))
        return planned


converter = LakeConverter()
