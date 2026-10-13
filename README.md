# b3-fetcher: Download e análise das Cotações Históricas da B3

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square) ![Python](https://img.shields.io/badge/python-3.13+-blue.svg?style=flat-square)

**b3-fetcher** é uma biblioteca Python para download, extração e transformação das
Cotações Históricas (COTAHIST) publicadas pela B3 (Brasil, Bolsa, Balcão).

## Sobre

A série histórica de cotações da B3 traz todo o histórico de preços dos títulos
negociados na bolsa desde 1986, sem ajuste de proventos. Os dados são publicados
em arquivos ZIP anuais (`COTAHIST_A<ano>.zip`) contendo um TXT de campos de
tamanho fixo (245 bytes, registros `00`/`01`/`99`).

Esta biblioteca facilita o acesso programático a esses dados, fazendo parte do
ecossistema Quantilica. O escopo é **download + parse + manifest**: a carga em
banco de dados pertence à camada de aplicação/loader, não ao fetcher.

## Documentação

Para instruções completas de instalação, tutoriais de uso, arquitetura e
referência da API, consulte a documentação oficial:

**[https://docs.quantilica.com](https://docs.quantilica.com)**

## Licença

MIT — veja [LICENSE](LICENSE).
