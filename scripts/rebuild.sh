#!/bin/sh
# Refaz base_aptos.csv e links_aptos.csv do zero a partir dos lotes brutos, na ordem de coleta.
# Uso: sh scripts/rebuild.sh LIMITE
set -e
L=${1:-1000000000}
D=2026-11-22
head -1 base_aptos.csv > /tmp/hb && head -1 links_aptos.csv > /tmp/hl && cp /tmp/hb base_aptos.csv && cp /tmp/hl links_aptos.csv
for b in campo-belo brooklin vila-mascote jardim-prudencia sul-7bairros; do python3 scripts/process_qa.py raw/qa_$b.txt $D $L | head -1; done
python3 scripts/process_zap.py raw/zap_campo-belo-brooklin.txt $D $L | head -1
python3 scripts/process_zap.py raw/zap_demais-bairros.txt $D $L | head -1
python3 scripts/add_links.py raw/vr_campo-belo.txt $D "VivaReal" https://www.vivareal.com.br
python3 scripts/process_iw.py raw/iw_bairros.txt $D $L | head -1
python3 scripts/process_lopes.py raw/lopes_bairros.txt raw/lopes_fix.txt $D $L | head -1
python3 scripts/process_qa.py raw/prohabitar.txt $D $L | head -1
python3 scripts/finalize.py
python3 scripts/enrich.py $D raw/enrich_quintoandar.json raw/enrich_lopes.json raw/enrich_zap.json raw/enrich_imovelweb.json raw/enrich_prohabitar.json
