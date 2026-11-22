# busca-apto

Base pessoal de imóveis para alugar na Zona Sul de São Paulo e o site para filtrar, dar nota e marcar favoritos.

## Pastas

| Caminho | O que é |
|---|---|
| base_aptos.csv, links_aptos.csv | Base de imóveis e de anúncios, mantida pela sessão de coleta |
| criterios.txt, log.txt, raw/, scripts/process_*.py | Critérios, registro e arquivos de trabalho da coleta |
| site/ | O site. index.html lê os CSVs e calcula a nota. Os pesos da nota ficam no bloco CFG do script |
| site/config.js | Endereço e chave pública do Supabase. Nunca colocar chave secreta aqui |
| supabase/esquema.sql | Tabelas de favoritos, notas e descartes, com as regras de acesso |
| backup/ | Cópia diária dos favoritos, notas e descartes, feita pelo GitHub Actions |
| scripts/copia_favoritos.py | Script da cópia diária |
| scripts/site_offline.py | Gera uma cópia do site com a base embutida, para abrir sem servidor |
| firebase.json | Configuração do Firebase Hosting |

## Publicação

A cada mudança na branch main, o GitHub Actions copia os CSVs para site/ e publica no Firebase Hosting.
