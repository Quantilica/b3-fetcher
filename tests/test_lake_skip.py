"""O build do lake pula, sem ler o bruto, o que já está em dia."""

from __future__ import annotations

import builtins
import shutil
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

import b3_fetcher.lake as lake_mod  # noqa: E402
from b3_fetcher.lake import converter  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"

_COTAHIST = FIXTURES / "COTAHIST_D02012024.txt"
_DERIV = FIXTURES / "derivatives_open_position_20261029.csv"
_INDICE = FIXTURES / "indices_carteiras_IBOV_response.json"

_COTAHIST_NOMES = ("COTAHIST_A2024@20241021.txt", "COTAHIST_A2023@20241021.txt")
_DERIV_NOMES = ("derivativos_agro-2026-10-29.csv", "derivativos_agro-2026-10-30.csv")
_INDICE_NOMES = (
    "indices_carteiras-IBOV-2026-11-03.json",
    "indices_carteiras-IBOV-2026-11-04.json",
)


def _bruto(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    for grupo, fixture, nomes in (
        ("cotacaohistorica", _COTAHIST, _COTAHIST_NOMES),
        ("derivativos_agro", _DERIV, _DERIV_NOMES),
        ("indices_carteiras", _INDICE, _INDICE_NOMES),
    ):
        pasta = raw / grupo
        pasta.mkdir(parents=True)
        for nome in nomes:
            shutil.copy(fixture, pasta / nome)
    return raw


@pytest.fixture
def leituras(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Registra toda leitura do bruto: leitores do conversor e ``open`` do arquivo."""
    vistas: list[str] = []

    def espia(nome: str, original):  # noqa: ANN001, ANN202
        def _f(*args, **kwargs):  # noqa: ANN002, ANN003
            vistas.append(nome)
            return original(*args, **kwargs)

        return _f

    for nome in ("read_records", "read_derivativos_agro", "read_indice"):
        monkeypatch.setattr(lake_mod, nome, espia(nome, getattr(lake_mod, nome)))
    monkeypatch.setattr(
        lake_mod, "read_csv_resilient", espia("csv", lake_mod.read_csv_resilient)
    )

    original_open = builtins.open

    def open_espia(file, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if "/raw/" in str(file) and not str(file).endswith(".manifest.json"):
            vistas.append(f"open:{Path(file).name}")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_espia)
    return vistas


@pytest.mark.parametrize(
    "dataset", ["cotacaohistorica", "derivativos_agro", "indices_carteiras"]
)
def test_segunda_rodada_nao_le_o_bruto(
    tmp_path: Path, leituras: list[str], dataset: str
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    res = converter.convert(raw, lake, datasets=[dataset])
    assert not res.errors, res.errors
    assert (res.converted, res.skipped) == (2, 0)
    assert leituras

    leituras.clear()
    res2 = converter.convert(raw, lake, datasets=[dataset])
    assert (res2.converted, res2.skipped, res2.errors) == (0, 2, [])
    assert leituras == []


@pytest.mark.parametrize(
    ("dataset", "leitor"),
    [
        ("cotacaohistorica", "read_records"),
        ("derivativos_agro", "read_derivativos_agro"),
        ("indices_carteiras", "read_indice"),
    ],
)
def test_force_reconverte_lendo_o_bruto(
    tmp_path: Path, leituras: list[str], dataset: str, leitor: str
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    converter.convert(raw, lake, datasets=[dataset])

    leituras.clear()
    res = converter.convert(raw, lake, datasets=[dataset], force=True)
    assert (res.converted, res.skipped, res.errors) == (2, 0, [])
    assert leituras.count(leitor) == 2


def test_bruto_novo_converte_e_o_resto_pula(
    tmp_path: Path, leituras: list[str]
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    converter.convert(raw, lake)
    shutil.copy(_DERIV, raw / "derivativos_agro" / "derivativos_agro-2026-10-31.csv")
    shutil.copy(
        _INDICE, raw / "indices_carteiras" / "indices_carteiras-IBOV-2026-11-05.json"
    )

    leituras.clear()
    res = converter.convert(raw, lake)
    assert not res.errors, res.errors
    assert (res.converted, res.skipped) == (2, 6)
    assert leituras.count("read_derivativos_agro") == 1
    assert leituras.count("read_indice") == 1
    assert leituras.count("read_records") == 0


def test_bruto_alterado_com_o_mesmo_nome_e_reconvertido(
    tmp_path: Path, leituras: list[str]
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    converter.convert(raw, lake, datasets=["derivativos_agro"])
    alvo = raw / "derivativos_agro" / "derivativos_agro-2026-10-29.csv"
    alvo.write_text(_DERIV.read_text() + "\n")

    leituras.clear()
    res = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert not res.errors, res.errors
    assert (res.converted, res.skipped) == (1, 1)
    assert leituras.count("read_derivativos_agro") == 1
