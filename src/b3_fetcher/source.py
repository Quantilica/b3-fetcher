"""Cliente do arquétipo A4 da B3 (token em duas etapas) e dos índices.

Este módulo só descreve e resolve a fonte; o ``FetcherApp`` faz o download.
Ele não toca o disco.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
from typing import Any
from urllib.parse import quote

from quantilica.core.exceptions import FetchError
from quantilica.core.http import HttpStatusError

from .constants import DOWNLOAD_URL, INDICES, PORTFOLIO_URL, REQUESTNAME_URL


class B3FileUnavailableError(FetchError):
    """A B3 não tem o arquivo pedido (``400`` do ``requestname``).

    Cobre fim de semana, feriado, data futura e ``fileName`` desconhecido: o
    endpoint não distingue os casos.
    """


class B3ProtocolError(FetchError):
    """Resposta da B3 fora do contrato (sem token, JSON inválido, sem carteira)."""


def build_requestname_url(file_name: str, date: dt.date) -> str:
    """URL da primeira etapa (``requestname``) para ``file_name`` em ``date``."""
    return f"{REQUESTNAME_URL}?fileName={quote(file_name)}&date={date.isoformat()}"


def token_from_response(payload: Any) -> str:
    """Extrai o token da resposta do ``requestname``.

    Usa ``token`` e, na falta dele, o parâmetro de ``redirectUrl``
    (``~/download?token=...``).

    Raises:
        B3ProtocolError: Se a resposta não trouxer token.
    """
    if isinstance(payload, dict):
        token = payload.get("token")
        if isinstance(token, str) and token:
            return token
        redirect = payload.get("redirectUrl")
        if isinstance(redirect, str) and "token=" in redirect:
            token = redirect.split("token=", 1)[1]
            if token:
                return token
    raise B3ProtocolError(f"resposta do requestname sem token: {str(payload)[:120]!r}")


def resolve_download_url(client: Any, request_url: str) -> str:
    """Resolve a URL de ``requestname`` na URL de download com token.

    Args:
        client: ``HttpClient`` (usa ``get``).
        request_url: Saída de :func:`build_requestname_url`.

    Raises:
        B3FileUnavailableError: Quando a B3 responde ``400``.
        B3ProtocolError: Quando a resposta não é o JSON esperado.
    """
    try:
        response = client.get(request_url)
    except HttpStatusError as exc:
        if exc.status_code == 400:
            raise B3FileUnavailableError(f"B3 sem arquivo para {request_url}") from exc
        raise
    try:
        payload = response.json()
    except ValueError as exc:
        raise B3ProtocolError(f"requestname não devolveu JSON: {request_url}") from exc
    return DOWNLOAD_URL + "?token=" + token_from_response(payload)


def build_portfolio_url(index_code: str, *, language: str = "pt-br") -> str:
    """URL do ``GetPortfolioDay`` (parâmetros em JSON compacto, base64)."""
    raw = json.dumps({"index": index_code, "language": language}, separators=(",", ":"))
    return PORTFOLIO_URL + base64.b64encode(raw.encode()).decode()


def index_url(indice: str) -> str:
    """URL da carteira do índice ``indice`` (sigla do Lake, ex. ``IBRX100``)."""
    try:
        return build_portfolio_url(INDICES[indice])
    except KeyError:
        raise ValueError(f"índice desconhecido: {indice!r}") from None


def portfolio_date(payload: Any) -> dt.date:
    """Data da carteira (``header.date``, ``dd/mm/aa``) de uma resposta.

    Raises:
        B3ProtocolError: Quando a B3 devolve 200 sem cabeçalho (índice
            inexistente, como ``IBRX100``) ou sem resultados.
    """
    header = payload.get("header") if isinstance(payload, dict) else None
    if not header or not payload.get("results"):
        raise B3ProtocolError(
            "GetPortfolioDay sem cabeçalho/resultados (índice válido?)"
        )
    text = str(header.get("date") or "")
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise B3ProtocolError(f"data de carteira ilegível: {text!r}")
