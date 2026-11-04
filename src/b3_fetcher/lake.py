"""Convert raw B3 COTAHIST archives into the Hive-partitioned lake.

Each raw annual ZIP/TXT lands in
``<lake>/b3/cotacaohistorica/ano=<ano>/<file_key>.parquet``.
Quotation records (01) are parsed, typed with exact decimals, dates and integers,
and stored in Parquet format.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import polars as pl
    from quantilica.analytics.lake import LakeWriter
    from quantilica.core.lake import DatasetDescriptor, partition_types_for
except ImportError as exc:
    raise ImportError(
        "b3_fetcher.lake requer o extra 'analysis': "
        "uv add 'b3-fetcher[analysis]' "
        "--index https://index.quantilica.com/simple/"
    ) from exc

from b3_fetcher import __version__
from b3_fetcher.constants import DATASET_ID, INDICES
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
    "derivativos_agro": {
        "alias": "derivativos_agro",
        "partition_keys": ["ano", "mes", "dia", "contrato"],
        "partition_types": partition_types_for(["ano", "mes", "dia", "contrato"]),
    },
    "indices_carteiras": {
        "alias": "indices_carteiras",
        "partition_keys": ["indice", "ano", "mes", "dia"],
        "partition_types": partition_types_for(["indice", "ano", "mes", "dia"]),
    },
}

DATASET_ALIASES = {
    "cotahist": DATASET_ID,
    "derivativos-agro": "derivativos_agro",
    "indices-carteiras": "indices_carteiras",
}

AGRO_SEGMENT = "AGRIBUSINESS"

_ANNUAL = re.compile(r"_A(?P<year>\d{4})", re.IGNORECASE)
_DAILY = re.compile(r"_D\d{4}(?P<year>\d{4})", re.IGNORECASE)
_YEAR = re.compile(r"(?:^|[-_@])(?P<year>(?:19|20)\d{2})(?:[-_@.]|$)")
_INDICE = re.compile(r"indices_carteiras-(?P<indice>[A-Za-z0-9]+)-", re.IGNORECASE)
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


class B3PathError(ValueError):
    """Arquivo cru cujo dataset ou partição não se deixa inferir do caminho."""


def resolve_b3_dataset(path: Path) -> str:
    """Resolve o dataset de um arquivo cru pelo diretório do grupo ou pelo nome.

    Raises:
        B3PathError: Quando o caminho não identifica nenhum dataset (nada de
            cair em ``cotacaohistorica`` por omissão).
    """
    names = {path.name.lower(), *(part.lower() for part in path.parent.parts)}
    for ds_id in ("derivativos_agro", "indices_carteiras"):
        if ds_id in names or any(n.startswith(ds_id + "-") for n in names):
            return ds_id
    if DATASET_ID in names or "cotahist" in path.name.lower():
        return DATASET_ID
    raise B3PathError(f"não foi possível identificar o dataset de {path.name}")


def resolve_b3_partitions(dataset_id: str, path: Path) -> dict[str, str]:
    """Resolve as partições a partir do nome do arquivo cru.

    O nome carrega a data do dado (``<grupo>[-<indice>]-AAAA-MM-DD.<ext>``).

    Raises:
        B3PathError: Quando faltam a data ou o índice. Nunca assume 01/01 nem
            a data de hoje.
    """
    if dataset_id == DATASET_ID:
        yr = year_from_path(path)
        return {"ano": yr} if yr else {}

    m_ymd = _YMD.search(path.name)
    if not m_ymd:
        raise B3PathError(
            f"{path.name}: sem data AAAA-MM-DD no nome; partição não inferida"
        )
    date = {"ano": m_ymd["ano"], "mes": m_ymd["mes"], "dia": m_ymd["dia"]}
    try:
        dt.date(int(date["ano"]), int(date["mes"]), int(date["dia"]))
    except ValueError as exc:
        raise B3PathError(f"{path.name}: data inválida ({exc})") from exc

    if dataset_id == "indices_carteiras":
        m_idx = _INDICE.search(path.name)
        if not m_idx or m_idx["indice"].upper() not in INDICES:
            raise B3PathError(f"{path.name}: índice desconhecido ou ausente")
        return {"indice": m_idx["indice"].upper(), **date}
    return date  # contrato é definido por linha, na conversão


_DERIVATIVOS_RENAME = {
    "RptDt": "data_referencia",
    "TckrSymb": "ticker",
    "ISIN": "codigo_isin",
    "Asst": "ativo_objeto",
    "XprtnCd": "codigo_vencimento",
    "SgmtNm": "segmento",
    "OpnIntrst": "contratos_em_aberto",
    "VartnOpnIntrst": "variacao_contratos_em_aberto",
    "DstrbtnId": "id_distribuicao",
    "CvrdQty": "qtd_coberta",
    "TtlBlckdPos": "total_posicoes_bloqueadas",
    "UcvrdQty": "qtd_descoberta",
    "TtlPos": "total_posicoes",
    "BrrwrQty": "qtd_tomador",
    "LndrQty": "qtd_doador",
    "CurQty": "qtd_atual",
    "FwdPric": "preco_termo",
}
_DERIVATIVOS_INT = (
    "contratos_em_aberto",
    "variacao_contratos_em_aberto",
    "qtd_coberta",
    "total_posicoes_bloqueadas",
    "qtd_descoberta",
    "total_posicoes",
    "qtd_tomador",
    "qtd_doador",
    "qtd_atual",
)
_PRICE = pl.Decimal(precision=28, scale=8)


def _br_decimal(column: str, dtype: Any = _PRICE) -> pl.Expr:
    """Texto com vírgula decimal (``1.234,56``) para decimal; vazio vira nulo."""
    return (
        pl.col(column)
        .str.replace_all(".", "", literal=True)
        .str.replace(",", ".", literal=True)
        .cast(dtype, strict=True)
    )


def read_derivativos_agro(path: Path) -> dict[str, pl.DataFrame]:
    """Lê o ``DerivativesOpenPosition`` e devolve o segmento agro por contrato.

    Tudo é lido como texto (``infer_schema=False``): ticker e ISIN nunca viram
    número. Só as colunas de quantidade são convertidas, com ``strict=True``.

    Returns:
        ``{ativo_objeto: DataFrame}`` (``BGI``, ``CCM``, ``ICF``, ``SJC``, ``ETH``…)
        só com as linhas do segmento ``AGRIBUSINESS``.

    Raises:
        ValueError: Se o arquivo não tiver o cabeçalho esperado (ex.: HTML).
    """
    skip = 0
    with open(path, "rb") as fh:
        first = fh.readline().decode("utf-8", errors="replace")
    if first.lower().startswith("status do arquivo"):
        skip = 1  # "Status do Arquivo: Final" antes do cabeçalho
    df = pl.read_csv(
        path, separator=";", infer_schema=False, skip_rows=skip, encoding="utf8"
    )
    missing = {"RptDt", "TckrSymb", "Asst", "SgmtNm"} - set(df.columns)
    if missing:
        raise ValueError(f"cabeçalho inesperado, faltam {sorted(missing)}")
    df = df.rename({k: v for k, v in _DERIVATIVOS_RENAME.items() if k in df.columns})
    df = df.filter(pl.col("segmento") == AGRO_SEGMENT)
    exprs: list[pl.Expr] = [
        pl.col("data_referencia").str.to_date("%Y-%m-%d", strict=True)
    ]
    exprs += [
        pl.col(c).cast(pl.Int64, strict=True) for c in _DERIVATIVOS_INT if c in df
    ]
    if "preco_termo" in df.columns:
        exprs.append(_br_decimal("preco_termo"))
    df = df.with_columns(exprs)
    return {
        contrato: part.drop_nulls("ativo_objeto")
        for (contrato,), part in df.partition_by(
            "ativo_objeto", as_dict=True, include_key=True
        ).items()
        if contrato
    }


def read_indice(path: Path) -> pl.DataFrame:
    """Lê a carteira de um índice (JSON do ``GetPortfolioDay``).

    Raises:
        ValueError: Se o JSON não tiver ``header``/``results``.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    header, results = payload.get("header"), payload.get("results")
    if not header or not results:
        raise ValueError("JSON sem header/results")
    data_carteira = dt.datetime.strptime(
        header["date"], "%d/%m/%y" if len(header["date"]) == 8 else "%d/%m/%Y"
    ).date()
    df = pl.DataFrame(
        results,
        schema={
            "segment": pl.String,
            "cod": pl.String,
            "asset": pl.String,
            "type": pl.String,
            "part": pl.String,
            "partAcum": pl.String,
            "theoricalQty": pl.String,
        },
    ).rename(
        {
            "segment": "segmento",
            "cod": "ticker",
            "asset": "nome",
            "type": "especie",
            "part": "participacao_pct",
            "partAcum": "participacao_acumulada_pct",
            "theoricalQty": "qtd_teorica",
        }
    )
    pct = pl.Decimal(precision=12, scale=6)
    return df.with_columns(
        _br_decimal("participacao_pct", pct),
        _br_decimal("participacao_acumulada_pct", pct),
        pl.col("qtd_teorica")
        .str.replace_all(".", "", literal=True)
        .cast(pl.Int64, strict=True),
        pl.lit(data_carteira).alias("data_carteira"),
        pl.lit(header.get("reductor"))
        .str.replace_all(".", "", literal=True)
        .str.replace(",", ".", literal=True)
        .cast(pl.Decimal(precision=28, scale=8), strict=True)
        .alias("redutor"),
        pl.lit(header.get("theoricalQty"))
        .str.replace_all(".", "", literal=True)
        .cast(pl.Int64, strict=True)
        .alias("qtd_teorica_total"),
    )


_CODE_SUBSTRINGS = ("isin", "ticker", "simbolo", "cnpj", "codigo_cvm", "cd_cvm")
_CODE_EXACT = frozenset({"contrato", "indice", "codigo_vencimento"})


def _is_code_column(name: str) -> bool:
    """Coluna de código (ISIN, ticker, CNPJ...), por nome; ``contratos_em_aberto``
    é quantidade e não casa."""
    norm = name.lower().replace("-", "_")
    return norm in _CODE_EXACT or any(k in norm for k in _CODE_SUBSTRINGS)


def _cast_b3_codes(df: pl.DataFrame) -> pl.DataFrame:
    """Garante que códigos B3 (ISIN, ticker, CNPJ, código CVM) sejam pl.String."""
    exprs = [
        pl.col(col).cast(pl.String)
        for col in df.columns
        if _is_code_column(col) and df.schema[col] != pl.String
    ]
    return df.with_columns(exprs) if exprs else df


def _without_partitions(df: pl.DataFrame, partitions: dict[str, Any]) -> pl.DataFrame:
    keys = {k.lower() for k in partitions}
    return df.drop([c for c in df.columns if c.lower() in keys])


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
            ConvertResult: Files converted, skipped, and error messages. Arquivos
            cujo dataset/partição não se infere do caminho viram erro contado.
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
            if p.is_file()
            and p.suffix.lower() in {".zip", ".txt", ".csv", ".json"}
            and not p.name.endswith(".manifest.json")
        )

        writers: dict[str, LakeWriter] = {}

        for path in files:
            try:
                ds_id = resolve_b3_dataset(path.relative_to(input_dir))
            except B3PathError as exc:
                if requested_canonical is None:
                    result.errors.append(str(exc))
                continue
            if requested_canonical and ds_id not in requested_canonical:
                continue
            try:
                partitions = resolve_b3_partitions(ds_id, path)
            except B3PathError as exc:
                result.errors.append(str(exc))
                continue

            if ds_id == DATASET_ID and "ano" not in partitions:
                result.errors.append(
                    f"{path.name}: não foi possível inferir o ano da partição"
                )
                continue

            spec = DATASET_SPECS[ds_id]
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
            converter_tag = f"b3-fetcher {__version__}"

            try:
                if ds_id == DATASET_ID:
                    frames = {None: read_records(path)}
                elif ds_id == "derivativos_agro":
                    frames = dict(read_derivativos_agro(path))
                else:
                    frames = {None: read_indice(path)}
                if not frames:
                    result.errors.append(f"{path.name}: sem linhas do segmento agro")
                    continue
                statuses = []
                for contrato, df in frames.items():
                    parts = dict(partitions)
                    if contrato is not None:
                        parts["contrato"] = contrato
                    written = writer.write_polars(
                        _without_partitions(_cast_b3_codes(df), parts),
                        path,
                        partitions=parts,
                        converter=converter_tag,
                    )
                    statuses.append(written.status)
            except Exception as exc:  # noqa: BLE001 - erro contado por arquivo
                message = str(exc).strip()
                first_line = message.splitlines()[0] if message else repr(exc)
                result.errors.append(f"{path.name}: {first_line}")
                continue

            if all(status == "skipped" for status in statuses):
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
                try:
                    ds_id = resolve_b3_dataset(path.relative_to(input_dir))
                except B3PathError:
                    planned.append(Planned(path, skip_reason="dataset_desconhecido"))
                    continue
                planned.append(Planned(path, dataset=ds_id))
            else:
                planned.append(Planned(path, skip_reason="nao_tabular"))
        return planned


converter = LakeConverter()
