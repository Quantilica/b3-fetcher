# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.3.0] - 2026-11-04

### Adicionado
- Coleta de `derivativos_agro` e `indices_carteiras` (TC-01). `derivativos_agro` baixa o
  `DerivativesOpenPosition` pelo protocolo A4 de duas etapas (`requestname` -> token ->
  `download/?token=`; `400` vira "sem arquivo" e é ignorado sem erro), uma entrada por dia
  útil da janela (`B3_LOOKBACK_DAYS`, padrão 5). `indices_carteiras` lê o `GetPortfolioDay`
  de IBOV, IBRX100 (código `IBXX` na API), SMLL, IDIV, IFIX e IFIL; o endpoint só serve a
  carteira vigente e o arquivo leva a data do cabeçalho da resposta.
- Lake: `derivativos_agro` com partições `ano/mes/dia/contrato` (segmento `AGRIBUSINESS`,
  um Parquet por ativo-objeto: BGI, CCM, ICF, SJC, ETH, CNL...) e `indices_carteiras` com
  `indice/ano/mes/dia`, pesos como decimal e quantidade teórica inteira.
- `B3FetcherApp`: `check` informa `skip-unavailable` para data sem arquivo.

### Removido
- Grupo `btc_posicoes_abertas` (e o dataset do Lake): não tinha URL e a sondagem de
  2026-11-03 não achou `fileName` do `requestname` para o empréstimo de ativos. Não há
  stub; reabrir quando houver fonte (nota de sondagem no repositório `planning`).

### Alterado
- `resolve_b3_dataset`/`resolve_b3_partitions` não caem mais em `cotacaohistorica`, em
  01/01 ou na data de hoje: arquivo cujo dataset, data ou índice não se infere do nome vira
  erro contado em `ConvertResult.errors`.
- Colunas de código passam a ser reconhecidas por nome exato/ISIN/ticker/CNPJ; antes
  `contratos_em_aberto` casava com `contrato` e virava texto.
- A conversão ignora os sidecars `*.manifest.json`.

### Corrigido
- Política de frescor volta a F2 (`HEAD_FALLBACK_GET`): `REMOTE_ONLY` (F3, para fontes sem validadores) causava re-download diário de fontes com Last-Modified/ETag, porque descartava o Last-Modified e o nome do arquivo caía em `@hoje`.

### Alterado
- Exige `quantilica-core>=0.16.0`.

## [0.2.1] - 2026-10-29

### Corrigido

- `read_records` lê como UTF-8 o registro que vem nessa codificação num arquivo Latin-1
  (`FROTA OCEÂNI`, em 2026). Lido como Latin-1, ele ficava com um caractere a mais e
  deslocava os campos seguintes; o vencimento `09999123` impedia a conversão do ano.

## [0.2.0] - 2026-10-27

### Adicionado

- `lake`: suporte à conversão para o Parquet Lake Hive padronizado do ecossistema
  (`cotahist/ano=<ano>/<file_key>.parquet`), gerando `_dataset.json` com metadados
  e schema auditáveis.
- Entry point `quantilica.lake` registrando `b3 = "b3_fetcher.lake:converter"`
  para orquestração unificada de conversão via CLI (`quantilica lake convert`)
  e workers.
- Comandos `convert` e `pipeline` integrados ao `FetcherApp` com suporte a
  `--lake`, `--dataset` e `--force`.
- Dependência `quantilica-core` atualizada para `>=0.13.0` e, no extra `analysis`, `quantilica-analytics` para `>=0.5.0`: são as primeiras versões com o contrato e o escritor do lake.

## [0.1.0] - 2026-10-20

### Corrigido (antes da primeira publicação)

- `reader`: campos com vírgula implícita (preços, volume, `preco_exercicio_pontos`)
  passam a `Decimal` exato, com precisão igual ao tamanho do campo e escala tirada
  do próprio layout (`(11)V99` em 13 posições → 2 casas; `(07)V06` → 6). Antes a
  divisão era feita em `Float64`: R$ 37,80 saía como `37.800000000000004`.
- `reader`: conversões estritas. Campo em branco vira nulo; qualquer outro valor que
  não caiba no tipo do layout (número, data) levanta erro em vez de virar nulo.
- Conferido em 2026-10-20 com os 40 arquivos anuais de 1986 a 2025: nenhum erro nem
  nulo; nos 9.834 pregões em comum com uma carga anterior de referência, 9.832 têm
  contagem, soma do último preço e soma do volume idênticas.

### Adicionado

- Coletor das Cotações Históricas (COTAHIST) da B3: download dos arquivos
  anuais `COTAHIST_A<ano>.zip` (série desde 1986) via `FetcherApp` (`sync`,
  `check`, `list`), com manifest SHA-256 e escrita atômica.
- `reader` opcional (extra `analysis`) que parseia o TXT posicional de 245
  bytes (registros `00`/`01`/`99`) para Polars, com tabelas auxiliares
  (BDI, especificação, índice de correção, tipo de mercado).
- CLI standalone e plugin Typer para o `quantilica-cli` (`quantilica b3`).
