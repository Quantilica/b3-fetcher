"""``read_derivativos_agro`` lê pelo ``read_csv_resilient`` sem mudar a saída.

``fixtures/golden_derivativos_agro.json`` foi gerado com o ``pl.read_csv`` direto
que a função usava (esquema e linhas de cada contrato, com e sem a linha
``Status do Arquivo`` antes do cabeçalho).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("quantilica.analytics.reader")

from b3_fetcher.lake import read_derivativos_agro  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
CSV = FIXTURES / "derivatives_open_position_20261029.csv"
GOLDEN = FIXTURES / "golden_derivativos_agro.json"

# Linhas do segmento agro e de outro segmento, em UTF-8 e com acento no meio.
_AGRO = (
    "RptDt;TckrSymb;ISIN;Asst;XprtnCd;SgmtNm;OpnIntrst;VartnOpnIntrst;DstrbtnId;"
    "CvrdQty;TtlBlckdPos;UcvrdQty;TtlPos;BrrwrQty;LndrQty;CurQty;FwdPric\n"
    "2026-10-29;BGIF27;BRBGIF000000;BGI;F27;AGRIBUSINESS;120;-5;;;;;;;;;1.234,56\n"
    "2026-10-29;CCMK27;BRCCMK000000;CCM;K27;AGRIBUSINESS;80;3;;;;;;;;;\n"
    "2026-10-29;AALR3T;BRAALRTNO008;AALR;;EQUITY FORWARD;6;;;;;;;;;213900;601,9\n"
)


def _snapshot(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for contrato, df in sorted(read_derivativos_agro(path).items()):
        out[contrato] = {
            "schema": [[c, str(t)] for c, t in df.schema.items()],
            "rows": [
                json.dumps(r, ensure_ascii=False, default=str) for r in df.to_dicts()
            ],
        }
    return out


def snapshot(tmp: Path) -> dict[str, dict]:
    with_status = tmp / "com_status.csv"
    with_status.write_text("Status do Arquivo: Final\n" + _AGRO, encoding="utf-8")
    plain = tmp / "sem_status.csv"
    plain.write_text(_AGRO, encoding="utf-8")
    return {
        "fixture": _snapshot(CSV),
        "com-status": _snapshot(with_status),
        "sem-status": _snapshot(plain),
    }


def test_derivativos_output_matches_golden(tmp_path: Path) -> None:
    assert snapshot(tmp_path) == json.loads(GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover - gera o golden com a leitura atual
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        GOLDEN.write_text(
            json.dumps(snapshot(Path(tmp)), ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
    sys.stdout.write(f"golden gravado em {GOLDEN}\n")
