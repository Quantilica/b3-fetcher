---
dataset:
  id: indices_carteiras
  fonte: b3
  titulo: Composição teórica dos índices da B3
  resumo: Carteira teórica vigente de seis índices da B3 (IBOV, IBRX100, SMLL, IDIV, IFIX e IFIL), com cada ativo, a participação e a quantidade teórica.
  orgao: B3 S.A. - Brasil, Bolsa, Balcão
  pagina_oficial: https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm
  licenca: "Não informado pela fonte. Veja os Termos e Condições de Uso da B3: https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/"
  periodicidade: "carteira vigente a cada consulta; a B3 revê as carteiras periodicamente (o Ibovespa, a cada quatro meses, segundo a metodologia)"
  cobertura: {inicio: "2026-11", fim: em-curso}
  unidade: um ativo na carteira de um índice em uma data
  granularidade: {espacial: nacional (bolsa), temporal: data da carteira}
  formato_bruto: "JSON da resposta do serviço GetPortfolioDay (cabeçalho com data, redutor e quantidade teórica total; lista de resultados), números com ponto de milhar e vírgula decimal"
  lake: {estado: convertido, particoes: [indice, ano, mes, dia], chave: [indice, data_carteira, ticker], colunas: 10}
  unidades_de_medida:
    participacao_pct: "% da carteira"
    participacao_acumulada_pct: "% da carteira (sempre nula nas amostras)"
    qtd_teorica: "ações"
    redutor: "não informada pela fonte"
    qtd_teorica_total: "ações"
  dados_pessoais: nenhum
  eras: []
  revisado_em: 2026-11-09
  versao_fetcher: 0.4.1
---

# Composição teórica dos índices da B3

## Resumo

Para cada um dos índices IBOV (Ibovespa B3), IBRX100 (IBrX 100), SMLL (Small Cap), IDIV (Dividendos), IFIX (Fundos Imobiliários) e IFIL (Fundos Imobiliários de Alta Liquidez), a B3 publica a carteira teórica vigente: a lista de ativos, o percentual de participação e a quantidade teórica de cada um. O dataset guarda uma fotografia dessa carteira a cada coleta. Serve para reconstituir os pesos de um índice e acompanhar mudanças de composição.

## Ficha técnica

<!-- gerado:ficha -->

| Campo | Valor |
|---|---|
| Dataset | `b3/indices_carteiras` |
| Órgão | B3 S.A. - Brasil, Bolsa, Balcão |
| Página oficial | https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm |
| Licença | Não informado pela fonte. Veja os Termos e Condições de Uso da B3: https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/ |
| Periodicidade | carteira vigente a cada consulta; a B3 revê as carteiras periodicamente (o Ibovespa, a cada quatro meses, segundo a metodologia) |
| Cobertura | 2026-11 a em-curso |
| Unidade (uma linha) | um ativo na carteira de um índice em uma data |
| Granularidade | espacial: nacional (bolsa); temporal: data da carteira |
| Formato bruto | JSON da resposta do serviço GetPortfolioDay (cabeçalho com data, redutor e quantidade teórica total; lista de resultados), números com ponto de milhar e vírgula decimal |
| Estado no lake | convertido |
| Partições | `indice`, `ano`, `mes`, `dia` |
| Chave | `indice`, `data_carteira`, `ticker` |
| Colunas | 10 |
| Unidades de medida | `participacao_pct`: % da carteira; `participacao_acumulada_pct`: % da carteira (sempre nula nas amostras); `qtd_teorica`: ações; `redutor`: não informada pela fonte; `qtd_teorica_total`: ações |
| Dados pessoais | nenhum |
| Eras | nenhuma |
| Revisado em | 2026-11-09 |
| Versão do fetcher | 0.4.1 |

## Origem e coleta

- O fetcher consulta o serviço `GetPortfolioDay` do site de índices da B3, um índice por vez. O serviço só devolve a carteira vigente; o parâmetro de data é ignorado. O IBrX 100 se chama `IBXX` na API; com `IBRX100` o serviço responde vazio.
- No bruto, cada coleta é `indices_carteiras-<ÍNDICE>-<AAAA-MM-DD>.json`, em que a data é a do dia da coleta.
- Conferido em 2026-11-09 pela listagem do bruto: 18 arquivos, os seis índices em 2026-11-04, 2026-11-05 e 2026-11-06. Não há histórico anterior.

## Conteúdo

- Unidade: um ativo na carteira de um índice. Contagens na carteira de 2026-11-06: IBOV 76 ativos, IBRX100 100, IDIV 51, IFIL 56, IFIX 94 e SMLL 103.
- A participação soma 100,000000 e a soma das quantidades teóricas é igual à quantidade teórica total do cabeçalho em todas as sete carteiras convertidas (conferido em 2026-11-09).
- O IBOV de 2026-11-04 e o de 2026-11-06 têm o mesmo número de ativos (76), o mesmo redutor e a mesma quantidade teórica total; os arquivos diferem na data do cabeçalho. Não verificamos peso a peso.
- Não há eras.

## Variáveis

Não localizamos dicionário de dados desta resposta; as descrições abaixo vêm dos rótulos da própria resposta (por exemplo, "Quantidade Teórica Total" e "Redutor" no cabeçalho) e da conferência dos dados. O que a fonte não define está marcado como "não informado pela fonte". As colunas `indice`, `ano`, `mes` e `dia` são partições.

| Coluna no lake | Na fonte | Tipo | Descrição | Unidade / códigos | Período |
|---|---|---|---|---|---|
| `indice` | nome do arquivo | texto (partição) | Sigla do índice no lake | `IBOV`, `IBRX100`, `SMLL`, `IDIV`, `IFIX`, `IFIL` | todo |
| `ano` | data do nome do arquivo | inteiro (partição) | Ano da coleta | ano de 4 dígitos | todo |
| `mes` | data do nome do arquivo | inteiro (partição) | Mês da coleta | 1 a 12 | todo |
| `dia` | data do nome do arquivo | inteiro (partição) | Dia da coleta | 1 a 31 | todo |
| `segmento` | `segment` | texto | Segmento do ativo; não informado pela fonte | sempre nulo nas amostras | todo |
| `ticker` | `cod` | texto | Código de negociação do ativo | como `ABEV3` | todo |
| `nome` | `asset` | texto | Nome do ativo (nome resumido da empresa ou do fundo) | — | todo |
| `especie` | `type` | texto | Espécie do ativo, com espaços de preenchimento da fonte | como `ON      NM`, `UNT     N2`, `CI` | todo |
| `participacao_pct` | `part` | decimal(12,6) | Percentual de participação do ativo na carteira (a soma é 100) | % | todo |
| `participacao_acumulada_pct` | `partAcum` | decimal(12,6) | Participação acumulada; não informado pela fonte | sempre nula nas amostras | todo |
| `qtd_teorica` | `theoricalQty` | inteiro | Quantidade teórica do ativo na carteira | ações (ponto de milhar na fonte) | todo |
| `data_carteira` | `header.date` | data | Data da carteira, do cabeçalho da resposta (`dd/mm/aa`) | — | todo |
| `redutor` | `header.reductor` | decimal(28,8) | Redutor do índice, do cabeçalho; unidade não informada pela fonte | número decimal | todo |
| `qtd_teorica_total` | `header.theoricalQty` | inteiro | Quantidade teórica total da carteira, do cabeçalho (rótulo "Quantidade Teórica Total") | ações | todo |

## No lake

- Dataset `b3/indices_carteiras`, particionado por `indice`, `ano`, `mes` e `dia`, um Parquet por índice e coleta.
- O JSON é lido de `results` e do cabeçalho; sem cabeçalho ou resultados, o arquivo falha.
- Números em formato brasileiro viram decimal exato ou inteiro com conversão estrita. Percentuais com 6 casas, redutor com 8.
- `data_carteira`, `redutor` e `qtd_teorica_total` são repetidos em todas as linhas da carteira.
- O índice vem do nome do arquivo e precisa ser um dos seis conhecidos; a data da partição também vem do nome (a data da coleta), enquanto `data_carteira` vem do conteúdo.
- Esquema de referência (`indices_carteiras.schema.json`): 10 colunas, de sete carteiras.

## Cuidados de uso

- **A data da partição é a da coleta.** Use `data_carteira` como data da carteira. Em todos os arquivos convertidos as duas coincidem, mas a B3 só devolve a carteira vigente, então coletar mais tarde não recupera carteiras antigas.
- **Sem histórico.** O bruto conferido tem três dias; para uma série de composições é preciso acumular coletas.
- **Duas colunas sempre nulas.** `segmento` e `participacao_acumulada_pct` são nulas nas 7 carteiras convertidas (2026-11-09).
- **Espaços na espécie.** `especie` mantém os espaços de preenchimento da fonte (`ON      NM`); aplique `str.replace_all(r"\s+", " ")` antes de agrupar.
- **Definições.** Quantidade teórica, redutor e participação não têm definição na resposta; a metodologia de cada índice está no site da B3.
- **Termos de uso.** Veja os termos citados na licença.

## Exemplos

Os dez maiores pesos do IBOV na carteira mais recente coletada:

```python
import polars as pl

c = pl.scan_parquet("lake/b3/indices_carteiras/**/*.parquet", hive_partitioning=True)
ibov = c.filter(pl.col("indice") == "IBOV")
ultima = ibov.select(pl.col("data_carteira").max()).collect().item()
top10 = (
    ibov.filter(pl.col("data_carteira") == ultima)
    .sort("participacao_pct", descending=True)
    .select("ticker", "nome", "participacao_pct")
    .head(10)
    .collect()
)
```

## Referências

- Composição da carteira do Ibovespa (B3): https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-amplos/indice-ibovespa-ibovespa-composicao-da-carteira.htm
- Termos e Condições de Uso da B3: https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/
