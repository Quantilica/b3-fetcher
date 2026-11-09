---
dataset:
  id: derivativos_agro
  fonte: b3
  titulo: Posições em aberto em derivativos agropecuários
  resumo: Contratos em aberto, por dia, dos derivativos listados do segmento AGRIBUSINESS da B3 (boi gordo, milho, café, soja e outros), com a variação diária.
  orgao: B3 S.A. - Brasil, Bolsa, Balcão
  pagina_oficial: https://b3.com.br/data/files/1E/D1/BA/58/C841B810E9C1AAA8AC094EA8/DerivativesOpenPositionFile%202023.pdf
  licenca: "Não informado pela fonte. O glossário diz que o arquivo é um dado regulatório divulgado conforme a política de dados regulatórios da B3; veja também os Termos e Condições de Uso (https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/)"
  periodicidade: diária, após o pregão (dias úteis)
  cobertura: {inicio: "2026-10", fim: em-curso}
  unidade: um instrumento (contrato com vencimento) do segmento AGRIBUSINESS em um dia
  granularidade: {espacial: nacional (bolsa), temporal: dia}
  formato_bruto: "CSV separado por ponto e vírgula, UTF-8, vírgula decimal, uma linha de cabeçalho; algumas respostas têm antes uma linha 'Status do Arquivo'"
  lake: {estado: convertido, particoes: [ano, mes, dia, contrato], chave: [data_referencia, ticker], colunas: 17}
  unidades_de_medida:
    contratos_em_aberto: contratos
    variacao_contratos_em_aberto: contratos
    qtd_coberta: "quantidade (sempre nula neste dataset)"
    total_posicoes_bloqueadas: "posições (sempre nula neste dataset)"
    qtd_descoberta: "quantidade (sempre nula neste dataset)"
    total_posicoes: "posições (sempre nula neste dataset)"
    qtd_tomador: "clientes (sempre nula neste dataset)"
    qtd_doador: "clientes (sempre nula neste dataset)"
    qtd_atual: "ações (sempre nula neste dataset)"
    preco_termo: "moeda não informada pela fonte (sempre nulo neste dataset)"
  dados_pessoais: nenhum
  eras: []
  revisado_em: 2026-11-09
  versao_fetcher: 0.4.1
---

# Posições em aberto em derivativos agropecuários

## Resumo

O arquivo `DerivativesOpenPosition` da B3 traz, depois de cada pregão, as posições em aberto de todos os contratos de derivativos listados. O fetcher guarda o arquivo diário e o lake mantém só as linhas do segmento `AGRIBUSINESS`, particionadas por contrato (ativo-objeto). Serve para acompanhar o interesse aberto dos futuros e opções agropecuários.

## Ficha técnica

<!-- gerado:ficha -->

| Campo | Valor |
|---|---|
| Dataset | `b3/derivativos_agro` |
| Órgão | B3 S.A. - Brasil, Bolsa, Balcão |
| Página oficial | https://b3.com.br/data/files/1E/D1/BA/58/C841B810E9C1AAA8AC094EA8/DerivativesOpenPositionFile%202023.pdf |
| Licença | Não informado pela fonte. O glossário diz que o arquivo é um dado regulatório divulgado conforme a política de dados regulatórios da B3; veja também os Termos e Condições de Uso (https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/) |
| Periodicidade | diária, após o pregão (dias úteis) |
| Cobertura | 2026-10 a em-curso |
| Unidade (uma linha) | um instrumento (contrato com vencimento) do segmento AGRIBUSINESS em um dia |
| Granularidade | espacial: nacional (bolsa); temporal: dia |
| Formato bruto | CSV separado por ponto e vírgula, UTF-8, vírgula decimal, uma linha de cabeçalho; algumas respostas têm antes uma linha 'Status do Arquivo' |
| Estado no lake | convertido |
| Partições | `ano`, `mes`, `dia`, `contrato` |
| Chave | `data_referencia`, `ticker` |
| Colunas | 17 |
| Unidades de medida | `contratos_em_aberto`: contratos; `variacao_contratos_em_aberto`: contratos; `qtd_coberta`: quantidade (sempre nula neste dataset); `total_posicoes_bloqueadas`: posições (sempre nula neste dataset); `qtd_descoberta`: quantidade (sempre nula neste dataset); `total_posicoes`: posições (sempre nula neste dataset); `qtd_tomador`: clientes (sempre nula neste dataset); `qtd_doador`: clientes (sempre nula neste dataset); `qtd_atual`: ações (sempre nula neste dataset); `preco_termo`: moeda não informada pela fonte (sempre nulo neste dataset) |
| Dados pessoais | nenhum |
| Eras | nenhuma |
| Revisado em | 2026-11-09 |
| Versão do fetcher | 0.4.1 |

## Origem e coleta

- O serviço de arquivos da B3 entrega o arquivo em duas etapas: um pedido com o nome do arquivo (`DerivativesOpenPosition`) e a data devolve um token, e o download usa o token. Datas sem arquivo (fim de semana, feriado, data futura) respondem erro 400, que o fetcher ignora sem erro.
- Por padrão o fetcher lista os últimos 5 dias úteis; o prazo é ajustável.
- No bruto, cada dia é `derivativos_agro-<AAAA-MM-DD>.csv`.
- Conferido em 2026-11-09 pela listagem do bruto: cinco dias (2026-10-29, 2026-10-30, 2026-11-03, 2026-11-04 e 2026-11-05). Não há histórico anterior a 2026-10-29 no bruto conferido.

## Conteúdo

- Unidade: um instrumento (ticker) em um dia. Duas amostras convertidas em 2026-11-09 (2026-10-29 e 2026-11-05) somam 1.489 linhas e 799 tickers; o ticker é único em cada dia.
- Contratos (valor de `ativo_objeto` e da partição `contrato`) nas amostras: BGI, CCM, CNL (uma linha), ETH, ICF e SJC.
- O arquivo original contém também outros segmentos (como `EQUITY CALL`, `EQUITY PUT` e `EQUITY FORWARD`); o conversor mantém só `AGRIBUSINESS`. Por isso as colunas de empréstimo e opções sobre ações (de `id_distribuicao` a `preco_termo`) ficam todas nulas neste dataset.
- Não há eras: o layout é o mesmo nas duas amostras.

## Variáveis

Descrições do glossário oficial da B3 para o arquivo `DerivativesOpenPosition` (versão de 05/10/2023). A coluna `ano`, `mes`, `dia` e `contrato` são partições.

| Coluna no lake | Na fonte | Tipo | Descrição | Unidade / códigos | Período |
|---|---|---|---|---|---|
| `ano` | data do nome do arquivo | inteiro (partição) | Ano da data do arquivo | ano de 4 dígitos | todo |
| `mes` | data do nome do arquivo | inteiro (partição) | Mês da data do arquivo | 1 a 12 | todo |
| `dia` | data do nome do arquivo | inteiro (partição) | Dia da data do arquivo | 1 a 31 | todo |
| `contrato` | `Asst` | texto (partição) | Ativo-objeto do instrumento; repete `ativo_objeto` | `BGI`, `CCM`, `CNL`, `ETH`, `ICF`, `SJC` (amostras) | todo |
| `data_referencia` | `RptDt` | data | Data de referência da informação | `AAAA-MM-DD` na fonte | todo |
| `ticker` | `TckrSymb` | texto | Código que identifica um instrumento negociado ou registrado em bolsa | como `BGIF27` | todo |
| `codigo_isin` | `ISIN` | texto | International Securities Identification Number do instrumento (estrutura BR AAAA BBB CC D, segundo o glossário) | 12 caracteres | todo |
| `ativo_objeto` | `Asst` | texto | Mercadoria associada ao instrumento | exemplos do glossário: DOL, BGI, OZ1, WDL, CNI, ICF, CCM | todo |
| `codigo_vencimento` | `XprtnCd` | texto | Código de expiração do contrato, no formato MYY (mês e dois dígitos do ano) ou MYOA (mês, ano, código da opção e sequência alfanumérica) | como `F27` (futuro) ou `VVK7` (opção) | todo |
| `segmento` | `SgmtNm` | texto | Nome do segmento | `AGRIBUSINESS` (único valor mantido) | todo |
| `contratos_em_aberto` | `OpnIntrst` | inteiro | Quantidade de contratos em aberto | contratos | todo |
| `variacao_contratos_em_aberto` | `VartnOpnIntrst` | inteiro | Variação da quantidade de contratos abertos de um dia para o outro | contratos; pode ser negativa | todo |
| `id_distribuicao` | `DstrbtnId` | texto | Código de distribuição do papel; o glossário diz que não há distribuição de derivativos | sempre nulo aqui | todo |
| `qtd_coberta` | `CvrdQty` | inteiro | Quantidade coberta | sempre nula aqui | todo |
| `total_posicoes_bloqueadas` | `TtlBlckdPos` | inteiro | Total de posições travadas | sempre nula aqui | todo |
| `qtd_descoberta` | `UcvrdQty` | inteiro | Quantidade descoberta | sempre nula aqui | todo |
| `total_posicoes` | `TtlPos` | inteiro | Total de posições | sempre nula aqui | todo |
| `qtd_tomador` | `BrrwrQty` | inteiro | Quantidade de clientes tomadores | sempre nula aqui | todo |
| `qtd_doador` | `LndrQty` | inteiro | Quantidade de clientes doadores | sempre nula aqui | todo |
| `qtd_atual` | `CurQty` | inteiro | Quantidade de ações vinculadas a contratos em aberto | sempre nula aqui | todo |
| `preco_termo` | `FwdPric` | decimal(28,8) | Preço médio das posições em aberto | vírgula decimal na fonte; sempre nulo aqui | todo |

## No lake

- Dataset `b3/derivativos_agro`, particionado por `ano`, `mes`, `dia` e `contrato`, um Parquet por contrato e dia.
- Só as linhas com `SgmtNm = AGRIBUSINESS` entram; linhas sem ativo-objeto são descartadas.
- O arquivo é lido todo como texto; só as quantidades viram inteiro e `preco_termo` decimal, com conversão estrita (valor inválido faz o arquivo falhar). Tickers e ISIN nunca viram número.
- O conversor falha se o arquivo não tiver o cabeçalho esperado (por exemplo, uma página HTML no lugar do CSV).
- Nomes de coluna renomeados do inglês para português (tabela acima).
- Esquema de referência (`derivativos_agro.schema.json`): 17 colunas, de uma conversão de duas datas.

## Cuidados de uso

- **Nove colunas sempre nulas.** `id_distribuicao`, `qtd_coberta`, `total_posicoes_bloqueadas`, `qtd_descoberta`, `total_posicoes`, `qtd_tomador`, `qtd_doador`, `qtd_atual` e `preco_termo` são nulas nas 1.489 linhas das amostras (2026-11-09). Elas pertencem a outros segmentos do mesmo arquivo.
- **Cobertura curta.** O bruto conferido só tem cinco dias; não há série histórica longa.
- **Sem arquivo em dias sem pregão.** Fim de semana e feriado não geram linhas.
- **Interesse aberto não é volume negociado.** `contratos_em_aberto` é um estoque ao fim do dia.
- **Licença.** Não informada pela fonte; consulte os termos de uso da B3 antes de redistribuir.

## Exemplos

Contratos em aberto de boi gordo (`BGI`) por vencimento no último dia coletado:

```python
import polars as pl

d = pl.scan_parquet("lake/b3/derivativos_agro/**/*.parquet", hive_partitioning=True)
ultimo = d.select(pl.col("data_referencia").max()).collect().item()
bgi = (
    d.filter((pl.col("data_referencia") == ultimo) & (pl.col("ativo_objeto") == "BGI"))
    .select("ticker", "codigo_vencimento", "contratos_em_aberto", "variacao_contratos_em_aberto")
    .sort("contratos_em_aberto", descending=True)
    .collect()
)
```

## Referências

- Glossário do arquivo DerivativesOpenPosition (B3, 05/10/2023): https://b3.com.br/data/files/1E/D1/BA/58/C841B810E9C1AAA8AC094EA8/DerivativesOpenPositionFile%202023.pdf
- Termos e Condições de Uso da B3: https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/
