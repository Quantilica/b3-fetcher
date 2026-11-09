# B3 — Brasil, Bolsa, Balcão (`b3`)

O `b3-fetcher` coleta três conjuntos de dados públicos da B3 e os converte para o lake em Parquet particionado: a série histórica de cotações da bolsa (COTAHIST), as posições em aberto em derivativos agropecuários e a composição teórica dos principais índices.

| Dataset | O que é | Origem | Período | Página |
|---|---|---|---|---|
| `cotacaohistorica` | Cotações diárias de todos os papéis-mercado negociados na bolsa (preços, quantidade, volume), sem ajuste de proventos | Arquivos anuais `COTAHIST_A<ano>.zip` da série histórica da B3 | 1986 em diante | [cotacaohistorica](datasets/cotacaohistorica.md) |
| `derivativos_agro` | Contratos em aberto de derivativos do segmento `AGRIBUSINESS` (boi gordo, milho, café, soja e outros), por contrato e dia | Arquivo diário `DerivativesOpenPosition` do serviço de arquivos da B3 | dias recentes coletados (veja a página) | [derivativos_agro](datasets/derivativos_agro.md) |
| `indices_carteiras` | Composição teórica vigente dos índices IBOV, IBRX100, SMLL, IDIV, IFIX e IFIL: ativo, participação e quantidade teórica | Serviço de composição de índices do site da B3 | carteira vigente em cada coleta | [indices_carteiras](datasets/indices_carteiras.md) |

## Como a B3 publica

- **COTAHIST.** Um ZIP por ano com um TXT de campos de largura fixa (245 bytes por linha, registros `00` cabeçalho, `01` cotação e `99` rodapé), descrito no documento oficial "Layout do arquivo de cotações históricas". Existem também arquivos mensais e diários, que o fetcher não usa. Os arquivos de anos encerrados não mudam; o do ano corrente é regerado ao longo do ano.
- **Posições em aberto em derivativos.** Um CSV por dia, divulgado após o pregão, obtido em duas etapas (pedido do nome do arquivo e depois download com token). A B3 não tem arquivo para fim de semana, feriado ou data futura.
- **Carteiras de índices.** O serviço devolve só a carteira vigente; o parâmetro de data é ignorado. Cada coleta guarda a carteira do momento, e a data da carteira vem no cabeçalho da resposta.

Termos de uso: a página da série histórica informa que os dados são de propriedade exclusiva da B3, destinados estritamente à consulta informativa conforme os [Termos e Condições de Uso](https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/), e veda a coleta automatizada. Leia os termos antes de redistribuir qualquer dado deste conjunto.

## Como os conjuntos se relacionam

- `ticker` (`derivativos_agro`, `indices_carteiras`) e `simbolo` (`cotacaohistorica`) são o código de negociação do papel. O ISIN aparece em `codigo_isin` (derivativos) e em `codisi` (cotações, ISIN a partir de maio de 1995, segundo o layout).
- As ações que compõem um índice podem ser ligadas às cotações pelo ticker e pela data.

## Quebras que valem para mais de um conjunto

Não há quebras comuns. As páginas de cada dataset registram as suas.
