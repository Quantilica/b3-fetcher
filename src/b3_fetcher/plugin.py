"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

import datetime as dt
import logging
import threading
from pathlib import Path
from typing import Any

from quantilica.cli.sdk import CheckPlanItem, FetcherApp
from quantilica.core.registry import FetcherInfo
from quantilica.core.sync import FreshnessPolicy

from .catalog import ALL_GROUP_ALIASES, ALL_GROUPS, list_datasets
from .constants import MAX_BUSINESS_DAYS_WITHOUT_FILE
from .source import (
    B3FileUnavailableError,
    B3ProtocolError,
    portfolio_date,
    resolve_download_url,
)
from .storage import DataRepository

logger = logging.getLogger(__name__)


def path_builder(
    output_dir: Path, entry: dict[str, Any], last_modified: dt.date | None
) -> Path:
    """Build the local file path for a downloaded dataset entry.

    Args:
        output_dir: Base directory where data is stored.
        entry: Dataset entry dictionary (carries ``year`` and ``ext``).
        last_modified: Optional last modified date to stamp the filename.

    Returns:
        Path to the local file for the dataset.
    """
    return DataRepository(output_dir).path_for_entry(entry, last_modified=last_modified)


def _next_business_day(day: dt.date) -> dt.date:
    day += dt.timedelta(days=1)
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    return day


def _previous_business_day(day: dt.date) -> dt.date:
    day -= dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def streak_without_file(
    unavailable: set[dt.date],
    local: set[dt.date],
    limit: int = MAX_BUSINESS_DAYS_WITHOUT_FILE,
) -> tuple[dt.date, dt.date, int] | None:
    """Detecta um dataset sem arquivo há ``limit`` dias úteis ou mais.

    A B3 responde ``400`` para fim de semana, feriado, data futura e arquivo
    desconhecido sem distinguir os casos; só a ausência prolongada (arquivo
    renomeado ou removido) denuncia. Decide só com o que a rodada viu (datas que
    responderam ``400``) e com os arquivos já gravados, sem rede.

    Args:
        unavailable: Datas que responderam ``400`` nesta rodada.
        local: Datas dos arquivos já gravados do dataset.
        limit: Quantos dias úteis seguidos sem arquivo contam como erro.

    Returns:
        ``(desde, ate, dias_uteis)`` quando a sequência sem arquivo que termina na
        última data com ``400`` tem ``limit`` dias úteis ou mais; ``None`` caso
        contrário (inclusive quando há arquivo igual ou posterior a essa data).
        Com arquivo local anterior, a sequência começa no dia útil seguinte a ele;
        sem nenhum, só conta os ``400`` seguidos vistos na rodada.
    """
    if not unavailable:
        return None
    last_bad = max(unavailable)
    last_local = max(local, default=None)
    if last_local is not None and last_local >= last_bad:
        return None
    if last_local is not None:
        start = _next_business_day(last_local)
    else:
        start = last_bad
        day = _previous_business_day(last_bad)
        while day in unavailable:
            start = day
            day = _previous_business_day(day)
    days = 0
    day = start
    while day <= last_bad:
        if day.weekday() < 5:
            days += 1
        day += dt.timedelta(days=1)
    if days < limit:
        return None
    return start, last_bad, days


class B3FetcherApp(FetcherApp):
    """``FetcherApp`` que sabe resolver os protocolos diários da B3.

    - ``requestname`` (A4): troca a URL do ``requestname`` pelo download com token;
      ``400`` (feriado, sem arquivo) é ignorado sem erro, a menos que o dataset
      fique ``MAX_BUSINESS_DAYS_WITHOUT_FILE`` dias úteis seguidos sem arquivo
      (então o ``sync`` o conta como erro: o arquivo pode ter sido renomeado).
    - ``portfolio``: carteira vigente do índice; o nome do arquivo usa a data do
      cabeçalho da resposta.

    Entradas sem ``protocol`` (COTAHIST) seguem o caminho padrão.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._unavailable_lock = threading.Lock()
        self._unavailable: dict[str, set[dt.date]] = {}

    def download_datasets(
        self,
        entries: list[dict[str, Any]],
        output_dir: Path,
        workers: int = 4,
        *,
        force: bool = False,
    ) -> tuple[int, int, list[tuple[str, str]]]:
        """Baixa as entradas e acusa o dataset que só recebe ``400`` há dias.

        Um ``400`` isolado é feriado ou fim de semana e não é erro. Depois do
        download (que pode ter gravado dias anteriores em paralelo), cada dataset
        cujo último ``400`` fecha ``MAX_BUSINESS_DAYS_WITHOUT_FILE`` dias úteis
        seguidos sem arquivo entra nos erros, com o dataset e a data de início.
        """
        with self._unavailable_lock:
            self._unavailable = {}
        if force:
            downloaded, total, errors = super().download_datasets(
                entries, output_dir, workers=workers, force=True
            )
        else:
            downloaded, total, errors = super().download_datasets(
                entries, output_dir, workers=workers
            )
        with self._unavailable_lock:
            seen = {group: set(days) for group, days in self._unavailable.items()}
        repo = DataRepository(output_dir)
        errors = list(errors)
        for group, days in sorted(seen.items()):
            streak = streak_without_file(days, repo.daily_dates(group))
            if streak is None:
                continue
            since, until, count = streak
            message = (
                f"B3 sem arquivo de {group} desde {since.isoformat()} "
                f"({count} dias úteis seguidos, até {until.isoformat()}): "
                "a B3 responde 400 também quando o fileName muda ou o arquivo "
                "sai do ar"
            )
            logger.error("%s: %s", group, message)
            errors.append((group, message))
            stats = self.last_download_stats
            if stats is not None:
                stats.succeeded_count = max(0, stats.succeeded_count - 1)
                stats.failed()
        return downloaded, total, errors

    def download_entry(
        self,
        entry: dict[str, Any],
        output_dir: Path,
        *,
        dry_run: bool = False,
        progress: Any = None,
        force: bool = False,
    ) -> Path:
        protocol = entry.get("protocol")
        if protocol not in ("requestname", "portfolio"):
            return super().download_entry(
                entry, output_dir, dry_run=dry_run, progress=progress, force=force
            )
        group = str(entry["group"])
        if protocol == "portfolio":
            payload = self.client.get(entry["url"]).json()
            entry = {**entry, **self._portfolio_date_fields(payload)}
        output = self.path_builder(output_dir, entry, None)
        if dry_run or (output.exists() and not force):
            return output
        if protocol == "requestname":
            try:
                url = resolve_download_url(self.client, entry["url"])
            except B3FileUnavailableError:
                logger.info("%s: B3 sem arquivo (feriado/sem pregão)", entry["id"])
                self._record_unavailable(group, entry)
                return output
        else:
            url = entry["url"]
        return self._download_file(url, output, progress, force=force, dataset_id=group)

    def _record_unavailable(self, group: str, entry: dict[str, Any]) -> None:
        """Guarda a data que respondeu ``400`` para a conferência ao fim do sync."""
        try:
            day = dt.date.fromisoformat(str(entry["date"]))
        except (KeyError, ValueError):
            return
        with self._unavailable_lock:
            self._unavailable.setdefault(group, set()).add(day)

    @staticmethod
    def _portfolio_date_fields(payload: Any) -> dict[str, Any]:
        day = portfolio_date(payload)
        return {"date": day.isoformat(), "year": day.year}

    def check_entry(self, entry: dict[str, Any], output_dir: Path) -> CheckPlanItem:
        protocol = entry.get("protocol")
        if protocol not in ("requestname", "portfolio"):
            return super().check_entry(entry, output_dir)
        if protocol == "portfolio":
            try:
                entry = {
                    **entry,
                    **self._portfolio_date_fields(self.client.get(entry["url"]).json()),
                }
            except B3ProtocolError:
                return self._plan(entry, output_dir, "skip-unavailable", "sem-carteira")
        output = self.path_builder(output_dir, entry, None)
        if output.exists():
            return self._plan(entry, output_dir, "skip-up-to-date", "arquivo-final")
        if protocol == "requestname":
            try:
                resolve_download_url(self.client, entry["url"])
            except B3FileUnavailableError:
                return self._plan(entry, output_dir, "skip-unavailable", "b3-400")
        return self._plan(entry, output_dir, "download", "ausente")

    def _plan(
        self, entry: dict[str, Any], output_dir: Path, action: str, reason: str
    ) -> CheckPlanItem:
        output = self.path_builder(output_dir, entry, None)
        return CheckPlanItem(
            dataset=str(entry["group"]),
            id=str(entry["id"]),
            url=str(entry["url"]),
            partition=str(entry.get("date")),
            local_path=str(output),
            remote_etag=None,
            remote_last_modified=None,
            remote_size=None,
            local_exists=output.exists(),
            action=action,
            reason=reason,
            entry=dict(entry),
        )


_DEFAULT_OUTPUT = Path("/data/b3")

fetcher = B3FetcherApp(
    default_output=_DEFAULT_OUTPUT,
    name="b3-fetcher",
    help="Cotações Históricas (COTAHIST), derivativos agro e índices da B3.",
    info=FetcherInfo(
        id="b3",
        nome="B3 - Cotações Históricas e Índices",
        orgao="B3 S.A. - Brasil, Bolsa, Balcão (B3)",
        homepage=(
            "https://www.b3.com.br/pt_br/market-data-e-indices/"
            "servicos-de-dados/market-data/historico/mercado-a-vista/"
            "cotacoes-historicas/"
        ),
        cadencia="daily",
        dominio="financas",
        redistribuicao="restrita",
        restricao_nota=(
            "Termos de uso da B3 vedam coleta automatizada; sem licença "
            "aberta. Uso interno."
        ),
    ),
    groups_dict=ALL_GROUPS,
    aliases_dict=ALL_GROUP_ALIASES,
    list_datasets=list_datasets,
    path_builder=path_builder,
    freshness_policy=FreshnessPolicy.HEAD_FALLBACK_GET,
)


def convert(
    input_dir: Path,
    lake_dir: Path,
    *,
    dataset: list[str] | None = None,
    force: bool = False,
) -> Any:
    """Converte arquivos brutos da B3 (COTAHIST, derivativos, índices) para o lake."""
    try:
        from b3_fetcher import lake
    except ImportError as exc:
        raise ImportError(
            "Conversão para o lake requer o extra 'analysis'. "
            "Instale com: quantilica install b3 --extra analysis"
        ) from exc

    return lake.converter.convert(input_dir, lake_dir, datasets=dataset, force=force)


fetcher.command_convert(convert)
fetcher.command_pipeline(convert)

app = fetcher.app
