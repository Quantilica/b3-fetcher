# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-10-12

### Adicionado

- Coletor das Cotações Históricas (COTAHIST) da B3: download dos arquivos
  anuais `COTAHIST_A<ano>.zip` (série desde 1986) via `FetcherApp` (`sync`,
  `check`, `list`), com manifest SHA-256 e escrita atômica.
- `reader` opcional (extra `analysis`) que parseia o TXT posicional de 245
  bytes (registros `00`/`01`/`99`) para Polars, com tabelas auxiliares
  (BDI, especificação, índice de correção, tipo de mercado).
- CLI standalone e plugin Typer para o `quantilica-cli` (`quantilica b3`).
