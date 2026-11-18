"""O build do lake pula, sem ler o bruto, o que já está em dia."""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.lake")
pytest.importorskip("duckdb")

import quantilica.core.manifests as manifests_mod  # noqa: E402
from quantilica.analytics.lake import LakeWriter  # noqa: E402

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
    _sidecars(raw)
    return raw


def _sidecars(raiz: Path) -> None:
    """Sidecar ``.manifest.json`` com o sha256 de cada bruto, como o fetcher grava:
    o hash do bruto sai dele, sem ler o arquivo."""
    for f in sorted(raiz.rglob("*")):
        if f.is_file() and not f.name.endswith(".manifest.json"):
            Path(f"{f}.manifest.json").write_text(
                json.dumps(
                    {
                        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                        "size_bytes": f.stat().st_size,
                    }
                ),
                encoding="utf-8",
            )


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
    original_io_open = io.open
    original_path_open = Path.open

    def do_bruto(arquivo) -> bool:  # noqa: ANN001
        # O sidecar pode (e deve) ser lido: é dele que sai o sha256 do bruto.
        nome = str(arquivo)
        return "/raw/" in nome and not nome.endswith(".manifest.json")

    def open_espia(file, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        if do_bruto(file):
            vistas.append(f"open:{Path(file).name}")
        return original_open(file, *args, **kwargs)

    def io_open_espia(file, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        if do_bruto(file):
            vistas.append(f"io.open:{Path(file).name}")
        return original_io_open(file, *args, **kwargs)

    def path_open_espia(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        if do_bruto(self):
            vistas.append(f"Path.open:{self.name}")
        return original_path_open(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_espia)
    monkeypatch.setattr(io, "open", io_open_espia)
    monkeypatch.setattr(Path, "open", path_open_espia)
    monkeypatch.setattr(
        manifests_mod, "sha256_file", espia("hash", manifests_mod.sha256_file)
    )
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
    _sidecars(raw)

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
    _sidecars(raw)

    leituras.clear()
    res = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert not res.errors, res.errors
    assert (res.converted, res.skipped) == (1, 1)
    assert leituras.count("read_derivativos_agro") == 1


def test_sem_sidecar_o_espiao_de_hash_dispara(
    tmp_path: Path, leituras: list[str]
) -> None:
    # Prova de que o espião funciona: sem sidecar o bruto é hasheado lendo-o.
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    converter.convert(raw, lake, datasets=["derivativos_agro"])
    for sidecar in raw.rglob("*.manifest.json"):
        sidecar.unlink()
    leituras.clear()
    converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert "hash" in leituras


def test_derivativos_interrompido_no_contrato_k_completa_na_rodada_seguinte(
    tmp_path: Path, leituras: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    escrever = LakeWriter.write_polars
    chamadas: list[str] = []

    def falha_no_quarto(self, data, src, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
        if src.name.endswith("10-29.csv"):
            chamadas.append(kw["partitions"]["contrato"])
            if len(chamadas) == 4:
                raise RuntimeError("disco cheio")
        return escrever(self, data, src, **kw)

    with monkeypatch.context() as m:
        m.setattr(LakeWriter, "write_polars", falha_no_quarto)
        r1 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r1.converted, r1.skipped, len(r1.errors)) == (1, 0, 1)

    # 3 dos 6 contratos do 10-29 estão no lake: sem a declaração seria pulo eterno
    leituras.clear()
    r2 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r2.converted, r2.skipped, r2.errors) == (1, 1, [])
    assert leituras.count("read_derivativos_agro") == 1  # só o arquivo incompleto

    leituras.clear()
    r3 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r3.converted, r3.skipped, r3.errors) == (0, 2, [])
    assert leituras == []


def test_lake_sem_declaracao_reconverte_uma_vez_e_depois_pula(
    tmp_path: Path, leituras: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    raw, lake = _bruto(tmp_path), tmp_path / "lake"
    escrever = LakeWriter.write_polars

    def sem_decl(self, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
        kw.pop("origin_outputs", None)
        return escrever(self, *a, **kw)

    with monkeypatch.context() as m:  # lake gravado antes da declaração
        m.setattr(LakeWriter, "write_polars", sem_decl)
        r0 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r0.converted, r0.skipped) == (2, 0)

    r1 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r1.converted, r1.skipped, r1.errors) == (2, 0, [])

    leituras.clear()
    r2 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert (r2.converted, r2.skipped, r2.errors) == (0, 2, [])
    assert leituras == []


def test_arquivo_sem_linhas_agro_segue_dando_erro_a_cada_build(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "raw"
    (raw / "derivativos_agro").mkdir(parents=True)
    cab = _DERIV.read_text().splitlines()[0]
    (raw / "derivativos_agro" / "derivativos_agro-2026-10-29.csv").write_text(
        cab + "\n"
    )
    _sidecars(raw)
    lake = tmp_path / "lake"
    r1 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    r2 = converter.convert(raw, lake, datasets=["derivativos_agro"])
    assert len(r1.errors) == len(r2.errors) == 1
    assert (r2.converted, r2.skipped) == (0, 0)
