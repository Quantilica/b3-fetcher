"""Convert raw B3 COTAHIST archives into the Hive-partitioned lake.

Each raw annual ZIP/TXT lands in
``<lake>/b3/cotacaohistorica/ano=<ano>/<file_key>.parquet``.
Quotation records (01) are parsed, typed with exact decimals, dates and integers,
and stored in Parquet format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import polars as pl
    from quantilica.analytics.lake import LakeError, LakeWriter
    from quantilica.core.lake import DatasetDescriptor
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
PARTITION_TYPES = {"ano": "varchar"}

_ANNUAL = re.compile(r"_A(?P<year>\d{4})", re.IGNORECASE)
_DAILY = re.compile(r"_D\d{4}(?P<year>\d{4})", re.IGNORECASE)
_YEAR = re.compile(r"(?:^|[-_@])(?P<year>(?:19|20)\d{2})(?:[-_@.]|$)")


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


class LakeConverter:
    """Converter registered under the ``quantilica.lake`` entry point."""

    source_id = SOURCE_ID

    def datasets(self) -> list[str]:
        """Dataset ids this converter writes to the lake."""
        return [DATASET_ID]

    def convert(
        self,
        input_dir: Path,
        lake_dir: Path,
        *,
        datasets: list[str] | None = None,
        force: bool = False,
    ) -> ConvertResult:
        """Convert raw B3 COTAHIST files into ``lake_dir``.

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

        if datasets and DATASET_ID not in datasets and "cotahist" not in datasets:
            return result

        files = sorted(
            p
            for p in input_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".zip", ".txt"}
        )

        writer = LakeWriter(
            lake_dir / SOURCE_ID / DATASET_ID,
            DatasetDescriptor(
                source_id=SOURCE_ID,
                dataset_id=DATASET_ID,
                alias="cotahist",
                partition_keys=PARTITION_KEYS,
                partition_types=PARTITION_TYPES,
            ),
            force=force,
        )

        for path in files:
            year = year_from_path(path)
            if not year:
                result.errors.append(
                    f"{path.name}: não foi possível inferir o ano da partição"
                )
                continue

            try:
                df = read_records(path)
                written = writer.write_polars(
                    df,
                    path,
                    partitions={"ano": year},
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


converter = LakeConverter()
