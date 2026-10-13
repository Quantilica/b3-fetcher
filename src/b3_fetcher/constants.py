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
