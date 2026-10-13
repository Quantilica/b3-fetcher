"""b3-fetcher - Biblioteca Python para as Cotações Históricas (COTAHIST) da B3.

Fornece ferramentas para baixar e parsear a série histórica de cotações
publicada pela B3 (Brasil, Bolsa, Balcão).
"""

from importlib.metadata import PackageNotFoundError, version

from quantilica.core.logging import get_logger

from .catalog import GROUP_ALIASES, GROUPS, list_datasets
from .constants import DATASET_ID, MIN_YEAR
from .fetcher import (
    build_annual_url,
    build_daily_url,
    build_monthly_url,
    valid_year,
)
from .storage import DataRepository

try:
    __version__ = version("b3-fetcher")
except PackageNotFoundError:
    __version__ = "0.0.0"

logger = get_logger(__name__)

__all__ = [
    # Version
    "__version__",
    # Catalog
    "DATASET_ID",
    "GROUP_ALIASES",
    "GROUPS",
    "MIN_YEAR",
    "list_datasets",
    # Source adapter
    "build_annual_url",
    "build_monthly_url",
    "build_daily_url",
    "valid_year",
    # Storage
    "DataRepository",
]

try:
    from .reader import read_dimension, read_records

    _HAS_ANALYSIS = True
except ImportError:
    _HAS_ANALYSIS = False
    read_records = None
    read_dimension = None

if _HAS_ANALYSIS:
    __all__.extend(["read_records", "read_dimension"])
