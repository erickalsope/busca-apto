#!/usr/bin/env python3
"""Acrescenta links de outra fonte para anúncios que já estão na base (mesmo id do grupo ZAP/VivaReal).
Entrada: linhas L§id§url. Uso: python3 scripts/add_links.py raw/arquivo.txt AAAA-MM-DD "VivaReal" https://www.vivareal.com.br
"""
import csv, sys, re
raw, hoje, fonte, host = sys.argv[1:5]
COLS = 'id_imovel;fonte;anunciante;codigo_anunciante;link;aluguel_anunciado;status_link;data_primeira_coleta;data_ultima_verificacao'.split(';')
links = list(csv.DictReader(open('links_aptos.csv', encoding='utf-8'), delimiter=';'))
known = {l['link'] for l in links}
n = 0
for line in open(raw, encoding='utf-8'):
    if not line.startswith('L§'):
        continue
    _, lid, url = line.rstrip('\n').split('§')[:3]
    url = host + url if url.startswith('/') else url
    if url in known:
        continue
    src = next((l for l in links if re.search(r'id-%s/?$' % lid, l['link'])), None)
    if not src:
        continue
    links.append(dict(id_imovel=src['id_imovel'], fonte=fonte, anunciante=src['anunciante'],
                      codigo_anunciante=src['codigo_anunciante'], link=url, aluguel_anunciado=src['aluguel_anunciado'],
                      status_link='ativo', data_primeira_coleta=hoje, data_ultima_verificacao=hoje))
    known.add(url)
    n += 1
w = csv.DictWriter(open('links_aptos.csv', 'w', encoding='utf-8', newline=''), fieldnames=COLS, delimiter=';', lineterminator='\n')
w.writeheader(); w.writerows(links)
print('links acrescentados', n)
