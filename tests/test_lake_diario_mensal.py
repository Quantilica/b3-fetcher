"""COTAHIST diário e mensal da coleta antiga: contidos no anual, sem Parquet próprio.

``cotacaohistorica-diario`` e ``cotacaohistorica-mensal`` guardam os arquivos
``COTAHIST_D``/``COTAHIST_M`` de 2014 a abril de 2023; cada registro deles está no
``COTAHIST_A<ano>`` do mesmo ano (``cotacaohistorica``), que é o que vira Parquet.
O inventário do conversor devolvia um motivo de exclusão inválido para eles, o que
derrubava o inventário inteiro (a auditoria caía na heurística e acusava ``sem_parquet``
em cada um).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

import polars as pl  # noqa: E402
from quantilica.analytics.lake import check_dataset  # noqa: E402
from quantilica.analytics.lake_audit import lake_audit  # noqa: E402

from b3_fetcher.constants import DATASET_ID  # noqa: E402
from b3_fetcher.lake import (
    SOURCE_ID,
    anuais_vigentes,
    converter,
    superado_pelo_anual,
)  # noqa: E402

FIXTURE_TXT = Path(__file__).parent / "fixtures" / "COTAHIST_D02012024.txt"


def _zip(path: Path, member: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, FIXTURE_TXT.read_bytes())
    return path


def _raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw" / SOURCE_ID
    _zip(
        raw / "cotacaohistorica" / "2024" / "cotacaohistorica_2024@20241231.zip",
        "COTAHIST_A2024.TXT",
    )
    _zip(
        raw
        / "cotacaohistorica-diario"
        / "2024"
        / "cotacaohistorica_20240102@20240103T000000.zip",
        "COTAHIST_D02012024.TXT",
    )
    _zip(
        raw
        / "cotacaohistorica-mensal"
        / "2024"
        / "cotacaohistorica_202401@20240201T000000.zip",
        "COTAHIST_M012024.TXT",
    )
    return raw


def test_superado_pelo_anual() -> None:
    anuais = {"2022": "20221230", "2023": "20231229"}
    diario = Path("cotacaohistorica-diario/2022/cotacaohistorica_20220103@1.zip")
    assert superado_pelo_anual(diario, anuais)
    mensal = Path("cotacaohistorica-mensal/2022/cotacaohistorica_202203@1.zip")
    assert superado_pelo_anual(mensal, anuais)
    assert not superado_pelo_anual(Path("cotacaohistorica/2022/x@1.zip"), anuais)
    assert not superado_pelo_anual(Path("derivativos_agro/2026/x.csv"), anuais)
    # Sem o anual do ano, o diário/mensal é a única cópia dos dados.
    sem = Path("cotacaohistorica-diario/2021/cotacaohistorica_20210104@1.zip")
    assert not superado_pelo_anual(sem, anuais)
    # Anual de carimbo anterior ao dia: ainda não cobre.
    assert not superado_pelo_anual(diario, {"2022": "20220102"})
    assert not superado_pelo_anual(mensal, {"2022": "20220326"})
    assert superado_pelo_anual(mensal, {"2022": "20220331"})
    # O último pregão do mês pode cair antes do fim dele (anual 2015: @20151230).
    dezembro = Path("cotacaohistorica-mensal/2015/cotacaohistorica_201512@1.zip")
    assert superado_pelo_anual(dezembro, {"2015": "20151230"})


def test_anuais_vigentes_so_conta_o_anual(tmp_path: Path) -> None:
    arquivos = [
        Path("cotacaohistorica/2022/cotacaohistorica_2022@20221215.zip"),
        Path("cotacaohistorica/2022/cotacaohistorica_2022@20221230.zip"),
        Path("cotacaohistorica-diario/2022/cotacaohistorica_20220103@20220104.zip"),
        Path("derivativos_agro/2026/derivativos_agro-2026-10-29.csv"),
    ]
    assert anuais_vigentes(arquivos) == {"2022": "20221230"}


def test_inventario_marca_diario_e_mensal_como_superados(tmp_path: Path) -> None:
    raw = _raw(tmp_path)
    (raw / "desconhecido").mkdir()
    (raw / "desconhecido" / "qualquer.zip").write_bytes(b"x")
    planned = {
        p.path.name: (p.dataset, p.skip_reason) for p in converter.inventory(raw)
    }
    assert planned["cotacaohistorica_2024@20241231.zip"] == (DATASET_ID, None)
    assert planned["cotacaohistorica_20240102@20240103T000000.zip"] == (
        None,
        "superado",
    )
    assert planned["cotacaohistorica_202401@20240201T000000.zip"] == (None, "superado")
    # Sem dataset e sem motivo: espera Parquet, e a auditoria o acusa.
    assert planned["qualquer.zip"] == (None, None)


def test_sem_o_anual_do_ano_o_diario_nao_e_superado(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / SOURCE_ID
    _zip(
        raw
        / "cotacaohistorica-diario"
        / "2021"
        / "cotacaohistorica_20210104@20210105T000000.zip",
        "COTAHIST_D04012021.TXT",
    )
    _zip(
        raw / "cotacaohistorica" / "2024" / "cotacaohistorica_2024@20241231.zip",
        "COTAHIST_A2024.TXT",
    )
    (planned,) = [
        p for p in converter.inventory(raw) if "diario" in str(p.path.parent.parent)
    ]
    assert (planned.dataset, planned.skip_reason) == (None, None)
    (tmp_path / "lake").mkdir()
    report = lake_audit(
        tmp_path / "lake",
        input_dir=tmp_path / "raw",
        sources=[SOURCE_ID],
        readers=False,
        integrity=False,
        converters={SOURCE_ID: converter},
    )
    faltam = [f.path for f in report.findings if f.category == "sem_parquet"]
    assert any("cotacaohistorica_20210104" in p for p in faltam)


def test_convert_ignora_diario_e_mensal_sem_erro(tmp_path: Path) -> None:
    raw = _raw(tmp_path)
    lake = tmp_path / "lake"
    res = converter.convert(raw, lake)
    assert res.errors == []
    assert res.converted == 1  # só o anual
    res = converter.convert(raw, lake)
    assert (res.converted, res.skipped, res.errors) == (0, 1, [])


def test_auditoria_nao_cobra_parquet_do_diario_e_do_mensal(tmp_path: Path) -> None:
    raw = _raw(tmp_path)
    lake = tmp_path / "lake"
    converter.convert(raw, lake)
    report = lake_audit(
        lake,
        input_dir=tmp_path / "raw",
        sources=[SOURCE_ID],
        readers=False,
        integrity=False,
        converters={SOURCE_ID: converter},
    )
    assert not [n for n in report.notes if "inventory()" in n]
    assert report.by_category().get("sem_parquet", 0) == 0
    assert report.ignored.get("superado") == 2


def test_carteira_vazia_da_b3_vira_parquet_vazio_com_o_esquema(tmp_path: Path) -> None:
    """``header`` e ``results`` nulos: a B3 respondeu 200 sem carteira para a data."""
    import shutil

    raiz = tmp_path / "raw"
    raw = raiz / SOURCE_ID / "indices_carteiras" / "2026"
    raw.mkdir(parents=True)
    fixtures = Path(__file__).parent / "fixtures"
    shutil.copy(
        fixtures / "indices_carteiras_IBOV_response.json",
        raw / "indices_carteiras-IBOV-2026-11-03.json",
    )
    (raw / "indices_carteiras-IFIL-2026-11-23.json").write_text(
        '{"page":{"pageNumber":-1,"pageSize":-1,"totalRecords":null,'
        '"totalPages":null},"header":null,"results":null}'
    )
    lake = tmp_path / "lake"
    res = converter.convert(raiz, lake, datasets=["indices_carteiras"])
    assert (res.converted, res.skipped, res.errors) == (2, 0, [])

    ds = lake / SOURCE_ID / "indices_carteiras"
    cheio = next(ds.glob("indice=IBOV/**/*.parquet"))
    vazio = next(ds.glob("indice=IFIL/ano=2026/mes=11/dia=23/*.parquet"))
    sv, sc = pl.read_parquet(vazio).schema, pl.read_parquet(cheio).schema
    assert pl.read_parquet(vazio).height == 0
    assert sv == sc
    assert check_dataset(ds) == []

    # A auditoria cobre o arquivo vazio: sem exceção no ledger.
    report = lake_audit(
        lake,
        input_dir=raiz,
        sources=[SOURCE_ID],
        readers=False,
        integrity=False,
        converters={SOURCE_ID: converter},
    )
    assert report.by_category().get("sem_parquet", 0) == 0

    # Reexecutar pula os dois; JSON sem a estrutura esperada segue sendo erro.
    res = converter.convert(raiz, lake, datasets=["indices_carteiras"])
    assert (res.converted, res.skipped) == (0, 2)
    (raw / "indices_carteiras-IFIL-2026-11-24.json").write_text('{"results": []}')
    res = converter.convert(raiz, lake, datasets=["indices_carteiras"])
    assert len(res.errors) == 1 and "sem header/results" in res.errors[0]


def test_inventario_anual_sem_carimbo_perde_para_o_carimbado(tmp_path: Path) -> None:
    """O anual sem carimbo é o mais antigo (``select_current``): o carimbo que
    decide se o diário está contido é o do carimbado, não ``99999999``."""
    raw = tmp_path / "raw"
    for rel in (
        "cotacaohistorica/2022/cotacaohistorica_2022.zip",
        "cotacaohistorica/2022/cotacaohistorica_2022@20220110.zip",
        "cotacaohistorica-diario/2022/cotacaohistorica_20220103@20220104.zip",
        "cotacaohistorica-diario/2022/cotacaohistorica_20220201@20220202.zip",
    ):
        f = raw / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    planned = {
        p.path.name: (p.dataset, p.skip_reason) for p in converter.inventory(raw)
    }
    assert planned["cotacaohistorica_2022.zip"] == (None, "superado")
    assert planned["cotacaohistorica_2022@20220110.zip"] == (DATASET_ID, None)
    assert planned["cotacaohistorica_20220103@20220104.zip"] == (None, "superado")
    # O anual vigente só cobre até 10/01: o diário de fevereiro não está contido.
    assert planned["cotacaohistorica_20220201@20220202.zip"] == (None, None)
