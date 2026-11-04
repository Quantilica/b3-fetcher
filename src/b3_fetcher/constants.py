"""Constants for the B3 COTAHIST fetcher."""

from __future__ import annotations

# Distribuição oficial da série histórica de cotações (COTAHIST).
# Arquivos anuais:  COTAHIST_A<ano>.zip
# Arquivos mensais: COTAHIST_M<mm><ano>.zip
# Arquivos diários: COTAHIST_D<dd><mm><ano>.zip
COTAHIST_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_"

# A série histórica começa em 1986 (COTAHIST_A1985.zip responde 404).
MIN_YEAR = 1986

DATASET_ID = "cotacaohistorica"
SOURCE_ID = "b3"
PRODUCER = "b3-fetcher"

# Diretório (dentro do pacote) com as tabelas de layout do arquivo COTAHIST.
AUXILIARY_TABLES_DIR = "auxiliary_tables"

# --- Arquivos diários da B3 (arquétipo A4: token em duas etapas) -------------
# ``GET requestname?fileName=<nome>&date=AAAA-MM-DD`` devolve ``200`` com
# ``{"redirectUrl": "~/download?token=...", "token": "...", "file": {...}}`` e
# ``400`` quando o arquivo não existe (fim de semana, feriado, data futura,
# ``fileName`` desconhecido). O download é ``GET download/?token=<token>``
# (``HEAD`` devolve 404 e ``Range`` é ignorado; o token pode ser reutilizado).
ARQUIVOS_API_URL = "https://arquivos.b3.com.br/api/"
REQUESTNAME_URL = ARQUIVOS_API_URL + "download/requestname"
DOWNLOAD_URL = ARQUIVOS_API_URL + "download/"

# Composição teórica dos índices (só devolve a carteira vigente; o parâmetro
# ``date`` é ignorado pelo endpoint).
PORTFOLIO_URL = (
    "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"
)

# dataset do Lake -> fileName do ``requestname`` (sondado em 2026-11-03).
FILE_NAMES = {"derivativos_agro": "DerivativesOpenPosition"}

# Sigla do Lake (``indice=``) -> código aceito pelo endpoint da B3. O IBrX 100
# se chama ``IBXX`` na API (``IBRX100`` devolve 200 com corpo vazio).
INDICES = {
    "IBOV": "IBOV",
    "IBRX100": "IBXX",
    "SMLL": "SMLL",
    "IDIV": "IDIV",
    "IFIX": "IFIX",
    "IFIL": "IFIL",
}

# Janela de datas listadas por ``list``/``sync`` (dias úteis, hoje inclusive).
DEFAULT_LOOKBACK_BUSINESS_DAYS = 5
LOOKBACK_ENV = "B3_LOOKBACK_DAYS"
