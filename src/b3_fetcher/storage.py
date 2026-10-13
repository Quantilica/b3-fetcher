"""Data repository layout for B3 COTAHIST artifacts.

Files are stored as ``cotacaohistorica/<year>/cotacaohistorica_<year>@<stamp>.zip``
so each new remote version (identified by ``Last-Modified``) lands as a distinct
local file.
"""

from __future__ import annotations

import datetime as dt
import os
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
        filename = build_stamped_filename(
            DATASET_ID, year, ext=ext, timestamp=last_modified
        )
        return self.dataset_path(DATASET_ID, str(year), filename)
