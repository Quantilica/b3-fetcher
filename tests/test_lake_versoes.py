"""Versões carimbadas do mesmo bruto: só a vigente vira Parquet.

O bruto guarda ``x@20241101.zip``, ``x@20241102.zip``...; todas mapeiam para o mesmo
Parquet. O conversor escolhe a vigente (``select_current``) antes de converter: as
anteriores não são lidas a cada rodada e o inventário as marca ``superado``.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

from quantilica.analytics.lake import scan_dataset  # noqa: E402

import b3_fetcher.lake as lake_mod  # noqa: E402
from b3_fetcher.constants import DATASET_ID  # noqa: E402
from b3_fetcher.lake import SOURCE_ID, converter  # noqa: E402

FIXTURE_TXT = Path(__file__).parent / "fixtures" / "COTAHIST_D02012024.txt"
GRUPO = "cotacaohistorica/2024"


def _zip(path: Path, linhas: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("COTAHIST_A2024.TXT", "\n".join(linhas) + "\n")
    return path


def _fixture_linhas() -> list[str]:
    return FIXTURE_TXT.read_text(encoding="latin-1").splitlines()


@pytest.fixture
def leituras(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    vistas: list[str] = []
    original = lake_mod.read_records

    def espia(path: Path, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        vistas.append(Path(path).name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(lake_mod, "read_records", espia)
    return vistas


def _linhas_no_lake(lake: Path) -> int:
    return scan_dataset(lake / SOURCE_ID / DATASET_ID).collect().height


def test_so_a_vigente_e_convertida(tmp_path: Path, leituras: list[str]) -> None:
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    linhas = _fixture_linhas()
    # A versão antiga vem depois na ordem de nome do diretório de propósito:
    # a escolha é pelo carimbo, não pela ordem em que os arquivos aparecem.
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241101.zip", linhas[:5] + linhas[-1:])
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241102.zip", linhas)

    res = converter.convert(raw, lake)
    assert (res.converted, res.skipped, res.errors) == (1, 1, [])
    assert leituras == ["cotacaohistorica_2024@20241102.zip"]
    assert _linhas_no_lake(lake) == 6


def test_segunda_rodada_nao_reconverte_nada(
    tmp_path: Path, leituras: list[str]
) -> None:
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    linhas = _fixture_linhas()
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241101.zip", linhas[:5] + linhas[-1:])
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241102.zip", linhas)
    converter.convert(raw, lake)

    leituras.clear()
    res = converter.convert(raw, lake)
    assert (res.converted, res.skipped, res.errors) == (0, 2, [])
    assert leituras == []


def test_versao_nova_converte_so_ela_e_substitui_sem_duplicar(
    tmp_path: Path, leituras: list[str]
) -> None:
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    linhas = _fixture_linhas()
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241101.zip", linhas[:5] + linhas[-1:])
    converter.convert(raw, lake)
    assert _linhas_no_lake(lake) == 4

    _zip(raw / GRUPO / "cotacaohistorica_2024@20241102.zip", linhas)
    leituras.clear()
    res = converter.convert(raw, lake)
    assert (res.converted, res.skipped, res.errors) == (1, 1, [])
    assert leituras == ["cotacaohistorica_2024@20241102.zip"]

    parquets = list((lake / SOURCE_ID / DATASET_ID).rglob("*.parquet"))
    assert len(parquets) == 1  # o membro antigo foi substituído, não somado
    assert _linhas_no_lake(lake) == 6


def test_sem_carimbo_perde_para_o_carimbado(
    tmp_path: Path, leituras: list[str]
) -> None:
    raw, lake = tmp_path / "raw", tmp_path / "lake"
    linhas = _fixture_linhas()
    _zip(raw / GRUPO / "cotacaohistorica_2024.zip", linhas[:5] + linhas[-1:])
    _zip(raw / GRUPO / "cotacaohistorica_2024@20241102.zip", linhas)
    res = converter.convert(raw, lake)
    assert (res.converted, res.skipped, res.errors) == (1, 1, [])
    assert leituras == ["cotacaohistorica_2024@20241102.zip"]


def test_inventario_marca_as_superadas(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    linhas = _fixture_linhas()
    antiga = _zip(raw / GRUPO / "cotacaohistorica_2024@20241101.zip", linhas)
    nova = _zip(raw / GRUPO / "cotacaohistorica_2024@20241102.zip", linhas)
    outro = _zip(raw / GRUPO / "cotacaohistorica_2025@20241101.zip", linhas)

    planned = {p.path: (p.dataset, p.skip_reason) for p in converter.inventory(raw)}
    assert planned[antiga] == (None, "superado")
    assert planned[nova] == (DATASET_ID, None)
    assert planned[outro] == (DATASET_ID, None)
