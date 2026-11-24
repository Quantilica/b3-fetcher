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

from quantilica.analytics.lake_audit import lake_audit  # noqa: E402

from b3_fetcher.constants import DATASET_ID  # noqa: E402
from b3_fetcher.lake import SOURCE_ID, converter, superado_pelo_anual  # noqa: E402

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
    assert superado_pelo_anual(Path("cotacaohistorica-diario/2022/x@1.zip"))
    assert superado_pelo_anual(Path("cotacaohistorica-mensal/2022/x@1.zip"))
    assert not superado_pelo_anual(Path("cotacaohistorica/2022/x@1.zip"))
    assert not superado_pelo_anual(Path("derivativos_agro/2026/x.csv"))


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


def test_carteira_vazia_da_b3_nao_e_erro_do_conversor(tmp_path: Path) -> None:
    """``header`` e ``results`` nulos: a B3 respondeu 200 sem carteira para a data."""
    import shutil

    raw = tmp_path / "raw" / "indices_carteiras" / "2026"
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
    res = converter.convert(tmp_path / "raw", lake, datasets=["indices_carteiras"])
    assert res.errors == []
    assert (res.converted, res.skipped) == (1, 1)

    # JSON sem a estrutura esperada segue sendo erro.
    (raw / "indices_carteiras-IFIL-2026-11-24.json").write_text('{"results": []}')
    res = converter.convert(tmp_path / "raw", lake, datasets=["indices_carteiras"])
    assert len(res.errors) == 1 and "sem header/results" in res.errors[0]
