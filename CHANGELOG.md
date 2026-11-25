# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.5.3] - 2026-11-25

### Corrigido

- **O conversor lê só a versão vigente de cada bruto.** O bruto guarda cada versão carimbada (`cotacaohistorica_2026@AAAAMMDD.zip`, 14 versões de ~90 MB no caso real) e todas viram o mesmo Parquet; o `convert` as lia todas, em ordem de nome, e o resultado só saía certo porque a mais nova era gravada por último, a cada rodada. Agora escolhe a vigente por `quantilica.core.lake.select_current` antes de converter: as anteriores não são lidas (contam em `skipped`, salvo os COTAHIST diários e mensais superados pelo anual, que o `convert` ignora sem contar), a segunda rodada não reconverte nada e uma versão nova converte só ela, substituindo o Parquet anterior sem duplicar linhas. O `inventory()` marca as versões anteriores como `superado`. O carimbo do anual que decide se um diário ou mensal está contido nele passa a ser o da versão vigente (antes, um anual sem carimbo valia `99999999` mesmo havendo outro carimbado, e o `lake build` e o `convert` podiam divergir).

## [0.5.2] - 2026-11-24

### Corrigido

- **Inventário do conversor não cai mais com os COTAHIST diários e mensais.** Os arquivos das pastas `cotacaohistorica-diario` e `cotacaohistorica-mensal` (coleta antiga, 2014 a abril de 2023) recebiam o motivo `dataset_desconhecido`, que não é um motivo válido de `Planned`: o `inventory()` lançava `ValueError` e a auditoria do lake, sem inventário, cobrava Parquet de cada um (`sem_parquet`). Cada registro deles já está no COTAHIST anual do mesmo ano, que é o que vira Parquet (converter os dois duplicaria linhas no `ano=`). Agora o inventário os marca como `superado`, **só quando o anual daquele ano existe no bruto** com carimbo igual ou posterior ao dia (no mensal, ao fim do mês menos 4 dias: o último pregão pode cair antes do fim do mês); sem ele, o diário ou mensal é a única cópia dos dados e segue esperando Parquet. O `convert` ignora os superados sem contar erro. Um arquivo cujo dataset não se reconhece segue esperando Parquet (a auditoria o acusa).
- **Resposta vazia da B3 em `indices_carteiras` vira Parquet vazio.** Quando o `GetPortfolioDay` responde 200 com `header` e `results` nulos (a B3 não tem carteira para a data), o conversor lançava `JSON sem header/results` e a tarefa do dataset inteiro falhava. Agora grava um Parquet vazio, com o esquema da carteira (`data_carteira`, `redutor` e `qtd_teorica_total` nulos), na partição que vem do nome do arquivo; a auditoria o cobre sem exceção. JSON sem a estrutura esperada continua sendo erro.

## [0.5.1] - 2026-11-19

### Adicionado

- Testes: identidade do registro conferida.

### Alterado

- A leitura do `DerivativesOpenPosition` (`read_derivativos_agro`) usa `quantilica.analytics.reader.read_csv_resilient` em vez de `pl.read_csv`. A saída não muda (teste contra um golden da leitura anterior); um arquivo em cp1252/latin-1 passa a ser lido, com aviso no log, em vez de falhar.
- Requer `quantilica-analytics>=0.15.0` (antes `>=0.5.0`): o `read_csv_resilient` sem recuo silencioso de encoding vem da 0.10.0, e a conferência de saídas completas (`LakeWriter.origin_complete`), da 0.15.0.
- CI e infraestrutura alinhados ao template (fetcher-template v0.2.1).

### Corrigido

- `lake`: o build sem mudança não lê mais o bruto. Antes de ler o COTAHIST, o CSV de derivativos ou o JSON de índice, confere no rodapé do Parquet se o arquivo já está em dia e, estando, só conta `skipped`. Nos derivativos, em que o contrato só sai das linhas, as pastas `contrato=` do dia são listadas no lake. Mesma contagem de `converted`/`skipped`/`errors`; `force` e bruto novo seguem convertendo.
- `lake`: os derivativos só são dados por completos (pulo sem ler o arquivo) quando todos os contratos do arquivo, declarados ao lake antes da primeira gravação (`origin_outputs`), existem com o sha256 atual (`LakeWriter.origin_complete`) e a partição do dia é a do nome. Uma conversão que parou no meio (falha no contrato k) deixa de virar pulo permanente: o arquivo é relido e só os contratos que faltam são gravados. Lake gravado sem a declaração reconverte uma vez. Exige `quantilica-analytics>=0.15.0`.
- CI: o pyproject declara o PyPI antes do índice Quantilica (`[[tool.uv.index]]`), e o workflow perde `--index` e `--index-strategy`. Com a estratégia padrão `first-index`, o `uv sync` só consulta o índice para o que não está no PyPI (`quantilica-analytics`) e deixa de receber o 503 intermitente que o GitHub Pages devolve a caminhos inexistentes.

## [0.5.0] - 2026-11-14

### Adicionado
- Documentação dos dados em `docs/`, conforme a norma de documentação dos dados: página, dicionário de todas as variáveis e esquema de referência para cada um dos três datasets (`cotacaohistorica`, `derivativos_agro` e `indices_carteiras`). Um teste a verifica.
- O fetcher declara os fatos da fonte (`FetcherInfo`: id canônico, apelidos, órgão, licença, página e cadência) para o registro de fetchers da Quantilica.

### Alterado
- A fonte é declarada como de redistribuição restrita no registro de fetchers (`redistribuicao="restrita"`): os termos de uso da B3 vedam a coleta automatizada e não há licença aberta. Os dados ficam para uso interno.
- Requer `quantilica-core>=0.20.0` (e `quantilica-cli>=0.18.0` como host).

## [0.4.1] - 2026-11-05

### Corrigido
- `convert` sem o extra `analysis` falha com a instrução de instalação (`quantilica install b3 --extra analysis`) em vez de um erro de import genérico, e o `sync` passa a ter diretório de saída padrão fixo.

## [0.4.0] - 2026-11-04

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


## [0.3.0] - 2026-11-04

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

### Corrigido

_(antes da primeira publicação)_

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
