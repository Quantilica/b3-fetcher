"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any

from quantilica.cli.sdk import CheckPlanItem, FetcherApp
from quantilica.core.sync import FreshnessPolicy

from .catalog import ALL_GROUP_ALIASES, ALL_GROUPS, list_datasets
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


class B3FetcherApp(FetcherApp):
    """``FetcherApp`` que sabe resolver os protocolos diários da B3.

    - ``requestname`` (A4): troca a URL do ``requestname`` pelo download com token;
      ``400`` (feriado, sem arquivo) é ignorado sem erro.
    - ``portfolio``: carteira vigente do índice; o nome do arquivo usa a data do
      cabeçalho da resposta.

    Entradas sem ``protocol`` (COTAHIST) seguem o caminho padrão.
    """

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
                return output
        else:
            url = entry["url"]
        return self._download_file(url, output, progress, force=force, dataset_id=group)

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


fetcher = B3FetcherApp(
    name="b3-fetcher",
    help="Cotações Históricas (COTAHIST), derivativos agro e índices da B3.",
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
    from b3_fetcher import lake

    return lake.converter.convert(input_dir, lake_dir, datasets=dataset, force=force)


fetcher.command_convert(convert)
fetcher.command_pipeline(convert)

app = fetcher.app
