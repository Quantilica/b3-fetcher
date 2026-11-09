---
dataset:
  id: cotacaohistorica
  fonte: b3
  titulo: Cotações históricas da B3 (COTAHIST)
  resumo: Cotações diárias de cada papel-mercado negociado na bolsa desde 1986, com preços de abertura, máxima, mínima, média e último negócio, número de negócios, quantidade e volume, sem ajuste de proventos.
  orgao: B3 S.A. - Brasil, Bolsa, Balcão
  pagina_oficial: https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/
  licenca: "Não há licença aberta declarada. A página da série histórica diz que os dados são de propriedade exclusiva da B3, destinados estritamente à consulta informativa conforme os Termos e Condições de Uso (https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/), e veda a coleta automatizada"
  periodicidade: "arquivo anual, regerado ao longo do ano corrente; a página não declara a frequência"
  cobertura: {inicio: "1986-01", fim: em-curso}
  unidade: um papel-mercado em um pregão (registro 01 do arquivo)
  granularidade: {espacial: nacional (bolsa), temporal: dia de pregão}
  formato_bruto: "ZIP anual com TXT de largura fixa, 245 bytes por linha, Latin-1 (alguns registros recentes em UTF-8); registros 00, 01 e 99"
  lake: {estado: convertido, particoes: [ano], chave: [], colunas: 26}
  unidades_de_medida:
    tipreg: "código do tipo de registro (sempre 1)"
    tipo_mercado_id: "código (tabela TPMERC)"
    preco_abertura: "moeda de simbolo_moeda, por unidade de cotação (veja fator_cotacao)"
    preco_maximo: "moeda de simbolo_moeda, por unidade de cotação"
    preco_minimo: "moeda de simbolo_moeda, por unidade de cotação"
    preco_medio: "moeda de simbolo_moeda, por unidade de cotação"
    preco_ultimo_negocio: "moeda de simbolo_moeda, por unidade de cotação"
    preco_melhor_oferta_compra: "moeda de simbolo_moeda, por unidade de cotação"
    preco_melhor_oferta_venda: "moeda de simbolo_moeda, por unidade de cotação"
    quantidade_negocios: negócios
    quantidade_titulos_negociados: títulos
    volume_negociado: "moeda de simbolo_moeda"
    preco_exercicio: "moeda de simbolo_moeda (opções) ou valor do contrato (termo secundário)"
    indice_correcao_id: "código (tabela INDOPC)"
    fator_cotacao: "1 = cotação unitária; 1000 = cotação por lote de mil"
    preco_exercicio_pontos: "pontos (1 ponto = 1/100 US$ nas opções referenciadas em dólar)"
    dismes: "número de sequência"
  dados_pessoais: nenhum
  eras:
    - {desde: "1986-01", mudanca: "Início da série. Na amostra de 1986 o símbolo da moeda é CZ$ ou CR$ (campo moeda de referência); em 2012 e 2026 é R$"}
    - {desde: "1995-05", mudanca: "O campo CODISI passa a trazer o ISIN, segundo o layout (antes, código interno do papel, de 8 a 10 caracteres na amostra de 1986)"}
    - {desde: "2020-10", mudanca: "Revisão 2.0 do documento de layout (05/10/2020) atualiza a tabela de especificações (ESPECI)"}
    - {desde: "2026-10", mudanca: "Registros isolados passam a vir em UTF-8 dentro do arquivo Latin-1 (observado em 2026-10-22, nome resumido FROTA OCEÂNI); o conversor os lê como UTF-8"}
  revisado_em: 2026-11-09
  versao_fetcher: 0.4.1
---

# Cotações históricas da B3 (COTAHIST)

## Resumo

A série histórica de cotações da B3 traz o histórico de preços dos títulos negociados na bolsa desde 1986, na moeda e na forma de cotação da época, sem ajuste para inflação nem para proventos (dividendos, bonificações, direitos de subscrição). Cada linha é um papel-mercado em um pregão: ação à vista, fracionário, opção, termo, fundo imobiliário, BDR e outros. Serve para reconstituir preços, volumes e liquidez ao longo do tempo.

## Ficha técnica

<!-- gerado:ficha -->

| Campo | Valor |
|---|---|
| Dataset | `b3/cotacaohistorica` |
| Órgão | B3 S.A. - Brasil, Bolsa, Balcão |
| Página oficial | https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/ |
| Licença | Não há licença aberta declarada. A página da série histórica diz que os dados são de propriedade exclusiva da B3, destinados estritamente à consulta informativa conforme os Termos e Condições de Uso (https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/), e veda a coleta automatizada |
| Periodicidade | arquivo anual, regerado ao longo do ano corrente; a página não declara a frequência |
| Cobertura | 1986-01 a em-curso |
| Unidade (uma linha) | um papel-mercado em um pregão (registro 01 do arquivo) |
| Granularidade | espacial: nacional (bolsa); temporal: dia de pregão |
| Formato bruto | ZIP anual com TXT de largura fixa, 245 bytes por linha, Latin-1 (alguns registros recentes em UTF-8); registros 00, 01 e 99 |
| Estado no lake | convertido |
| Partições | `ano` |
| Chave | — |
| Colunas | 26 |
| Unidades de medida | `tipreg`: código do tipo de registro (sempre 1); `tipo_mercado_id`: código (tabela TPMERC); `preco_abertura`: moeda de simbolo_moeda, por unidade de cotação (veja fator_cotacao); `preco_maximo`: moeda de simbolo_moeda, por unidade de cotação; `preco_minimo`: moeda de simbolo_moeda, por unidade de cotação; `preco_medio`: moeda de simbolo_moeda, por unidade de cotação; `preco_ultimo_negocio`: moeda de simbolo_moeda, por unidade de cotação; `preco_melhor_oferta_compra`: moeda de simbolo_moeda, por unidade de cotação; `preco_melhor_oferta_venda`: moeda de simbolo_moeda, por unidade de cotação; `quantidade_negocios`: negócios; `quantidade_titulos_negociados`: títulos; `volume_negociado`: moeda de simbolo_moeda; `preco_exercicio`: moeda de simbolo_moeda (opções) ou valor do contrato (termo secundário); `indice_correcao_id`: código (tabela INDOPC); `fator_cotacao`: 1 = cotação unitária; 1000 = cotação por lote de mil; `preco_exercicio_pontos`: pontos (1 ponto = 1/100 US$ nas opções referenciadas em dólar); `dismes`: número de sequência |
| Dados pessoais | nenhum |
| Eras | 1986-01: Início da série. Na amostra de 1986 o símbolo da moeda é CZ$ ou CR$ (campo moeda de referência); em 2012 e 2026 é R$; 1995-05: O campo CODISI passa a trazer o ISIN, segundo o layout (antes, código interno do papel, de 8 a 10 caracteres na amostra de 1986); 2020-10: Revisão 2.0 do documento de layout (05/10/2020) atualiza a tabela de especificações (ESPECI); 2026-10: Registros isolados passam a vir em UTF-8 dentro do arquivo Latin-1 (observado em 2026-10-22, nome resumido FROTA OCEÂNI); o conversor os lê como UTF-8 |
| Revisado em | 2026-11-09 |
| Versão do fetcher | 0.4.1 |

## Origem e coleta

- O fetcher baixa `COTAHIST_A<ano>.zip` do endereço de distribuição oficial da série histórica, um por ano, de 1986 até o ano corrente. O arquivo de 1985 não existe na fonte.
- No bruto, cada ano é `cotacaohistorica_<AAAA>@<AAAAMMDD>.zip`. O sufixo é a data do cabeçalho `Last-Modified` do arquivo na fonte (ou a data da coleta, quando ela não vem); cada versão nova do arquivo fica como um arquivo distinto.
- Conferido em 2026-11-09 pela listagem do bruto: um arquivo por ano de 1986 a 2025 e, em 2026, seis versões (de 2026-10-27 a 2026-11-04). Sem lacunas de anos.
- O ZIP tem um TXT (nos arquivos antigos, um membro único sem extensão). O conversor lê só os registros `01`; os registros `00` (cabeçalho) e `99` (rodapé, com o total de registros) são descartados.

## Conteúdo

- Unidade: um papel-mercado em um pregão. Para o mesmo código de negociação pode haver linhas em mercados diferentes (por exemplo, à vista e fracionário), identificados por `tipo_mercado_id` e `bdi_id`.
- Amostras convertidas em 2026-11-09 (não são a série completa): 1986 com 177.981 linhas (248 pregões), 2012 com 330.633 (246 pregões) e 2026 com 3.398.579 (210 pregões, de 2026-01-02 a 2026-11-04, versão de 04/11).
- A data de cada linha pertence ao ano do arquivo nas três amostras (nenhuma linha fora do ano).
- Eras: veja o cabeçalho. A mudança da moeda nos primeiros anos aparece no campo `simbolo_moeda`; a B3 entrega o valor na moeda da época, sem conversão.

## Variáveis

Descrições e códigos vêm do documento oficial "Layout do arquivo - Cotações Históricas", revisão de 05/10/2020 ([SeriesHistoricas_Layout.pdf](https://www.b3.com.br/data/files/33/67/B9/50/D84057102C784E47AC094EA8/SeriesHistoricas_Layout.pdf)). A coluna "Na fonte" traz o nome do campo no layout. Colunas decimais têm vírgula implícita no arquivo e viram decimal exato no lake. A coluna `ano` é a partição.

| Coluna no lake | Na fonte | Tipo | Descrição | Unidade / códigos | Período |
|---|---|---|---|---|---|
| `ano` | ano do nome do arquivo | inteiro (partição) | Ano do arquivo `COTAHIST_A<ano>` | ano de 4 dígitos | todo |
| `tipreg` | `TIPREG` | inteiro | Tipo de registro; fixo "01" no layout | sempre 1 | todo |
| `data` | `DATA` (data do pregão) | data | Data do pregão (`AAAAMMDD` na fonte) | — | todo |
| `bdi_id` | `CODBDI` | texto | Código BDI, "utilizado para classificar os papéis na emissão do Boletim Diário de Informações" | 2 caracteres, como `02`; tabela CODBDI do layout (veja cuidados de uso) | todo |
| `simbolo` | `CODNEG` | texto | Código de negociação do papel | até 12 caracteres | todo |
| `tipo_mercado_id` | `TPMERC` | inteiro | Código do mercado em que o papel está cadastrado | 10 vista; 12 exercício de opções de compra; 13 exercício de opções de venda; 17 leilão; 20 fracionário; 30 termo; 50 futuro com retenção de ganho; 60 futuro com movimentação contínua; 70 opções de compra; 80 opções de venda (tabela TPMERC do layout) | todo |
| `nome_resumido` | `NOMRES` | texto | Nome resumido da empresa emissora do papel | até 12 caracteres (truncado pela fonte) | todo |
| `especificacao_id` | `ESPECI` | texto | Especificação do papel | tabela ESPECI do layout, por exemplo `ON`, `PN`, `UNT`, `CI`, `BDR`; os dados trazem também sufixos de nível de governança (`ON NM`, `PN N1`) | todo |
| `prazo` | `PRAZOT` | texto | Prazo em dias do mercado a termo | 3 caracteres, como `030`; vazio fora do termo e das opções | todo |
| `simbolo_moeda` | `MODREF` | texto | Moeda de referência: moeda usada na data do pregão | `CZ$`, `CR$` (1986), `R$` | todo |
| `preco_abertura` | `PREABE` | decimal(13,2) | Preço de abertura do papel-mercado no pregão | moeda da época | todo |
| `preco_maximo` | `PREMAX` | decimal(13,2) | Preço máximo do papel-mercado no pregão | moeda da época | todo |
| `preco_minimo` | `PREMIN` | decimal(13,2) | Preço mínimo do papel-mercado no pregão | moeda da época | todo |
| `preco_medio` | `PREMED` | decimal(13,2) | Preço médio do papel-mercado no pregão | moeda da época | todo |
| `preco_ultimo_negocio` | `PREULT` | decimal(13,2) | Preço do último negócio do papel-mercado no pregão | moeda da época | todo |
| `preco_melhor_oferta_compra` | `PREOFC` | decimal(13,2) | Preço da melhor oferta de compra do papel-mercado | moeda da época; 0,00 quando não há | todo |
| `preco_melhor_oferta_venda` | `PREOFV` | decimal(13,2) | Preço da melhor oferta de venda do papel-mercado | moeda da época; 0,00 quando não há | todo |
| `quantidade_negocios` | `TOTNEG` | inteiro | Número de negócios efetuados com o papel-mercado no pregão | negócios | todo |
| `quantidade_titulos_negociados` | `QUATOT` | inteiro | Quantidade total de títulos negociados neste papel-mercado | títulos | todo |
| `volume_negociado` | `VOLTOT` | decimal(18,2) | Volume total de títulos negociados neste papel-mercado | moeda da época | todo |
| `preco_exercicio` | `PREEXE` | decimal(13,2) | Preço de exercício para o mercado de opções ou valor do contrato para o mercado de termo secundário | moeda da época | todo |
| `indice_correcao_id` | `INDOPC` | inteiro | Indicador de correção de preços de exercícios ou valores de contrato para opções ou termo secundário | 1 US$ (correção pela taxa do dólar); 2 TJLP; 8 IGP-M (opções protegidas); 9 URV; nas amostras só aparece 0, que a tabela não define | todo |
| `data_vencimento` | `DATVEN` | data | Data do vencimento para os mercados de opções ou termo secundário | data; as amostras trazem 9999-12-31 nas linhas sem vencimento (observação, a fonte não define) | todo |
| `fator_cotacao` | `FATCOT` | inteiro | Fator de cotação do papel | 1 = cotação unitária; 1000 = cotação por lote de mil ações; as amostras de 2026 trazem também 100, 10000 e 1000000, que o layout não descreve | todo |
| `preco_exercicio_pontos` | `PTOEXE` | decimal(13,6) | Preço de exercício em pontos para opções referenciadas em dólar, ou valor de contrato em pontos para termo secundário | pontos; 1 ponto = 1/100 US$ | todo |
| `codisi` | `CODISI` | texto | Código do papel no sistema ISIN ou código interno do papel | ISIN (12 caracteres) a partir de 15-05-1995; antes, código interno | todo |
| `dismes` | `DISMES` | inteiro | Número de distribuição do papel: sequência do papel correspondente ao estado de direito vigente | número de sequência | todo |

## No lake

- Dataset `b3/cotacaohistorica`, particionado por `ano`; um Parquet por versão do arquivo.
- A partição `ano` vem do nome do arquivo (`..._A<ano>` ou o ano no nome), não da coluna `data`.
- Só os registros `01` entram. Campos de texto são aparados e têm espaços repetidos reduzidos a um; campos numéricos em branco viram nulo; qualquer valor que não caiba no tipo do layout faz a conversão falhar, em vez de virar nulo.
- Datas viram `date`; campos com vírgula implícita viram decimal exato (precisão igual ao tamanho do campo, escala igual às casas decimais do layout), nunca ponto flutuante.
- Códigos (`bdi_id`, `simbolo`, `codisi`) ficam como texto, preservando zeros à esquerda.
- Texto em branco vira texto vazio (`""`), não nulo; é o caso de `prazo` fora do termo (132.566 de 177.981 linhas em 1986) e de `nome_resumido` em 14 linhas de 2026.
- Os registros vêm em Latin-1; o conversor trata como UTF-8 as poucas linhas que, lidas em Latin-1, passariam de 245 caracteres e decodificam em UTF-8 com exatamente 245.
- O esquema de referência (`cotacaohistorica.schema.json`) tem 26 colunas, gerado de uma conversão das amostras de 1986, 2012 e 2026.

## Cuidados de uso

- **Sem ajuste de proventos.** A fonte avisa que as cotações são fornecidas na moeda e forma de cotação da época, sem ajuste para inflação nem para proventos (dividendos, bonificações, subscrição). Retornos calculados direto do preço de fechamento erram nos dias de desdobramentos, grupamentos e proventos.
- **Moeda da época.** Em 1986 as amostras trazem `CZ$` e `CR$`; compare preços entre épocas só depois de converter moedas.
- **Cotação por lote.** Quando `fator_cotacao` é 1000, o preço é por lote de mil; divida o preço pelo fator para obter o preço unitário. Em 2026 há linhas com fatores 100, 10000 e 1000000 que o layout não descreve (evidência: amostra de 2026, 2026-11-09).
- **Uma ação, várias linhas.** O mesmo papel pode aparecer em mercados diferentes. Para o preço de um papel no mercado à vista em lote padrão, filtre `tipo_mercado_id = 10` e `bdi_id = '02'`; no PETR4 de 2026 isso dá uma linha por pregão (210 linhas em 210 pregões, amostra de 2026-11-09).
- **Códigos fora das tabelas do layout.** Nas amostras há códigos de BDI que a tabela da revisão de 05/10/2020 não lista: `30` (5 linhas em 2012) e `34`, `36`, `35`, `93`, `13` e `92` em 2026; e o tipo de mercado `21` (2.106 linhas em 2026). Não atribuímos significado a eles; a fonte não os descreve nesse documento.
- **Especificação além da tabela.** As amostras trazem especificações como `ON NM`, `PN N1`, `UNT N2` e `DRN` que não constam da tabela anexa; a tabela do layout cobre só parte dos valores (em 2026, 2.930.502 de 3.398.579 linhas têm valor fora da tabela distribuída com o fetcher).
- **Tabelas auxiliares do fetcher.** O fetcher distribui cópias das tabelas do layout (`codbdi`, `especi`, `indopc`, `tpmerc`) em `read_dimension`. A cópia de `especi` (100 valores) difere da revisão de 05/10/2020: não tem, por exemplo, `CI ATZ`, `FIDC` nem `ON ATZ`, e traz `PNF`, `PNG` e `PNH`, que a revisão não lista; a descrição de alguns valores `... P` está truncada. Não use essas cópias como referência única.
- **Vencimento 9999-12-31.** Linhas sem vencimento trazem essa data; descarte-a antes de calcular prazos.
- **Chave.** Não há chave única simples: na amostra de 1986, combinar data, símbolo, mercado, BDI, especificação, prazo, vencimento, preço de exercício e ISIN deixa uma duplicata; em 2012 e 2026 essa combinação é única.
- **Dado suspeito na fonte.** Na amostra de 1986 há uma linha com preço máximo menor que o mínimo, e em 2026, 51 linhas com preço do último negócio igual a zero. Nenhuma foi corrigida.
- **Termos de uso.** Veja os termos citados na licença antes de redistribuir.

## Exemplos

Fechamento de PETR4 no mercado à vista em lote padrão, preço unitário (divide pelo fator de cotação):

```python
import polars as pl

cot = pl.scan_parquet("lake/b3/cotacaohistorica/**/*.parquet", hive_partitioning=True)
petr4 = (
    cot.filter(
        (pl.col("simbolo") == "PETR4")
        & (pl.col("tipo_mercado_id") == 10)
        & (pl.col("bdi_id") == "02")
        & (pl.col("ano") == 2026)
    )
    .select(
        "data",
        (pl.col("preco_ultimo_negocio") / pl.col("fator_cotacao")).alias("fechamento"),
    )
    .sort("data")
    .collect()
)
```

## Referências

- Página da série histórica: https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/
- Layout do arquivo de cotações históricas (revisão de 05/10/2020): https://www.b3.com.br/data/files/33/67/B9/50/D84057102C784E47AC094EA8/SeriesHistoricas_Layout.pdf
- Termos e Condições de Uso da B3: https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/
