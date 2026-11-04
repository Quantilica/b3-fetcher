"""Download em duas etapas da B3 (requestname -> token) e carteiras de índices.

Os corpos de resposta vêm de gravações reais de 2026-11-03 (``tests/fixtures``);
o token do ``requestname`` foi truncado.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx2
import pytest
from quantilica.core.http import HttpClient

from b3_fetcher.catalog import list_datasets
from b3_fetcher.constants import DOWNLOAD_URL
from b3_fetcher.plugin import B3FetcherApp, path_builder
from b3_fetcher.source import (
    B3FileUnavailableError,
    B3ProtocolError,
    build_portfolio_url,
    build_requestname_url,
    portfolio_date,
    resolve_download_url,
    token_from_response,
)

FIXTURES = Path(__file__).parent / "fixtures"
REQUESTNAME = (FIXTURES / "requestname_response.json").read_bytes()
TOKEN = json.loads(REQUESTNAME)["token"]
CSV = (FIXTURES / "derivatives_open_position_20261029.csv").read_bytes()
IBOV = (FIXTURES / "indices_carteiras_IBOV_response.json").read_bytes()
EMPTY_PORTFOLIO = (FIXTURES / "portfolio_ibrx100_wrong_code.txt").read_bytes()


class FakeB3:
    """Transporte que imita o ``requestname``/``download`` e o GetPortfolioDay."""

    def __init__(self, available: set[str]) -> None:
        self.available = available  # datas (AAAA-MM-DD) com arquivo
        self.calls: list[str] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        self.calls.append(f"{request.method} {url}")
        if request.url.path.endswith("/download/requestname"):
            if request.url.params["date"] in self.available:
                return httpx2.Response(200, content=REQUESTNAME)
            return httpx2.Response(400, content=b"")
        if request.url.path.endswith("/download/") and request.method == "GET":
            assert request.url.params["token"] == TOKEN
            return httpx2.Response(200, content=CSV)
        if request.url.path.endswith("/download/"):  # HEAD: a B3 devolve 404
            return httpx2.Response(404)
        if "GetPortfolioDay" in url:
            return httpx2.Response(
                200, content=EMPTY_PORTFOLIO if "IklCUlgxMDAi" in url else IBOV
            )
        return httpx2.Response(404)


def make_app(fake: FakeB3) -> B3FetcherApp:
    client = HttpClient(
        transport=httpx2.MockTransport(fake), attempts=1, retry_base_delay=0
    )
    return B3FetcherApp(
        name="b3-fetcher",
        groups_dict={"derivativos_agro": {}, "indices_carteiras": {}},
        aliases_dict={},
        list_datasets=list_datasets,
        path_builder=path_builder,
        client=client,
    )


def test_token_from_response_prefers_token_then_redirect() -> None:
    assert token_from_response({"token": "abc"}) == "abc"
    assert token_from_response({"redirectUrl": "~/download?token=xyz"}) == "xyz"
    with pytest.raises(B3ProtocolError):
        token_from_response({"file": {}})
    with pytest.raises(B3ProtocolError):
        token_from_response(None)


def test_resolve_download_url_returns_token_url() -> None:
    app = make_app(FakeB3({"2026-10-29"}))
    url = resolve_download_url(
        app.client,
        build_requestname_url("DerivativesOpenPosition", dt.date(2026, 10, 29)),
    )
    assert url == f"{DOWNLOAD_URL}?token={TOKEN}"


def test_resolve_download_url_maps_400_to_clear_error() -> None:
    app = make_app(FakeB3(set()))
    with pytest.raises(B3FileUnavailableError):
        resolve_download_url(
            app.client,
            build_requestname_url("BTC", dt.date(2026, 10, 29)),
        )


def test_download_entry_two_steps_and_idempotent(tmp_path: Path) -> None:
    fake = FakeB3({"2026-10-29"})
    app = make_app(fake)
    entry = next(
        e
        for e in list_datasets("derivativos_agro", today=dt.date(2026, 10, 29))
        if e["date"] == "2026-10-29"
    )
    out = app.download_entry(entry, tmp_path)
    assert (
        out
        == tmp_path / "derivativos_agro" / "2026" / "derivativos_agro-2026-10-29.csv"
    )
    assert out.read_bytes() == CSV
    assert out.with_name(out.name + ".manifest.json").exists()

    calls_before = len(fake.calls)
    assert app.download_entry(entry, tmp_path) == out
    assert len(fake.calls) == calls_before  # arquivo final: sem rede


def test_download_entry_without_file_is_not_an_error(tmp_path: Path) -> None:
    app = make_app(FakeB3(set()))
    entry = list_datasets("derivativos_agro", today=dt.date(2026, 11, 2))[-1]
    out = app.download_entry(entry, tmp_path)
    assert not out.exists()


def test_check_entry_statuses(tmp_path: Path) -> None:
    app = make_app(FakeB3({"2026-10-29"}))
    entries = {
        e["date"]: e
        for e in list_datasets("derivativos_agro", today=dt.date(2026, 10, 30))
    }
    assert app.check_entry(entries["2026-10-29"], tmp_path).action == "download"
    assert app.check_entry(entries["2026-10-30"], tmp_path).action == "skip-unavailable"
    app.download_entry(entries["2026-10-29"], tmp_path)
    assert app.check_entry(entries["2026-10-29"], tmp_path).action == "skip-up-to-date"


def test_portfolio_name_uses_header_date(tmp_path: Path) -> None:
    app = make_app(FakeB3(set()))
    entry = next(
        e
        for e in list_datasets("indices_carteiras", today=dt.date(2026, 11, 4))
        if e["indice"] == "IBOV"
    )
    out = app.download_entry(entry, tmp_path)
    assert out == (
        tmp_path
        / "indices_carteiras"
        / "2026"
        / "indices_carteiras-IBOV-2026-11-03.json"
    )
    assert json.loads(out.read_bytes())["header"]["date"] == "03/11/26"


def test_portfolio_without_header_is_protocol_error() -> None:
    assert portfolio_date(json.loads(IBOV)) == dt.date(2026, 11, 3)
    with pytest.raises(B3ProtocolError):
        portfolio_date(json.loads(EMPTY_PORTFOLIO))
    assert build_portfolio_url("IBOV").endswith(
        "eyJpbmRleCI6IklCT1YiLCJsYW5ndWFnZSI6InB0LWJyIn0="
    )
