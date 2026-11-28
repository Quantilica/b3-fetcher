"""Data repository layout for B3 COTAHIST artifacts.

Files are stored as ``cotacaohistorica/<year>/cotacaohistorica_<year>@<stamp>.zip``
so each new remote version (identified by ``Last-Modified``) lands as a distinct
local file.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import Any

from quantilica.core.storage import BaseDataRepository, build_stamped_filename

from .constants import DATASET_ID


class DataRepository(BaseDataRepository):
    """Repository for B3 COTAHIST archives."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        """Initialize the data repository.

        Args:
            root: The root directory for the repository.
        """
        super().__init__(root)

    def path_for_entry(
        self,
        entry: dict[str, Any],
        *,
        last_modified: dt.date | None = None,
    ) -> Path:
        """Compute the local path for a COTAHIST dataset entry.

        Args:
            entry: Dataset entry metadata (must carry ``year`` and ``ext``).
            last_modified: Last modified date to stamp, or None.

        Returns:
            The destination path for the entry.
        """
        year = entry["year"]
        ext = entry.get("ext", "zip")
        if entry.get("protocol") in ("requestname", "portfolio"):
            return self.path_for_daily_entry(entry)
        timestamp = last_modified or dt.date.today()
        filename = build_stamped_filename(
            DATASET_ID, year, ext=ext, timestamp=timestamp
        )
        return self.dataset_path(DATASET_ID, str(year), filename)

    def path_for_daily_entry(self, entry: dict[str, Any]) -> Path:
        """Path of a daily file, ``<grupo>/<ano>/<grupo>[-<indice>]-<data>.<ext>``.

        The data date is part of the name and the file is final, so the path does
        not depend on ``Last-Modified`` (the B3 token endpoint has no ``HEAD``).
        """
        group = str(entry["group"])
        date = str(entry["date"])
        label = (
            f"{group}-{entry['indice']}-{date}"
            if "indice" in entry
            else (f"{group}-{date}")
        )
        return self.dataset_path(
            group, str(entry["year"]), f"{label}.{entry.get('ext', 'csv')}"
        )

    def daily_dates(self, group: str) -> set[dt.date]:
        """Datas dos arquivos diários já gravados de ``group`` (sem rede).

        Lê só os nomes ``<grupo>-<data>.<ext>`` em ``<grupo>/<ano>/``; manifestos
        laterais e arquivos parciais ficam de fora.
        """
        base = self.dataset_path(group)
        dates: set[dt.date] = set()
        if not base.is_dir():
            return dates
        for path in base.glob("*/*"):
            found = _DAILY_DATE.search(path.name)
            if found is None or not path.is_file():
                continue
            try:
                dates.add(dt.date.fromisoformat(found.group(1)))
            except ValueError:
                continue
        return dates


_DAILY_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})\.[A-Za-z0-9]+$")
