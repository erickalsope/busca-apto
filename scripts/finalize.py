#!/usr/bin/env python3
"""Ajustes finais: observações manuais e recontagem de anúncios e imobiliárias ativas."""
import csv
base = list(csv.DictReader(open('base_aptos.csv', encoding='utf-8'), delimiter=';'))
links = list(csv.DictReader(open('links_aptos.csv', encoding='utf-8'), delimiter=';'))
MANUAL = {'https://www.quintoandar.com.br/imovel/895613721': 'verificar condominio (anúncio mostra R$ 1)'}
for b in base:
    for lk, note in MANUAL.items():
        if b['link_principal'] == lk and note not in b['observacoes']:
            b['observacoes'] = (b['observacoes'] + '. ' if b['observacoes'] else '') + note
    ls = [l for l in links if l['id_imovel'] == b['id'] and l['status_link'] == 'ativo']
    b['qtd_anuncios'] = str(len(ls))
    an = []
    for l in ls:
        if l['anunciante'] not in an:
            an.append(l['anunciante'])
    b['imobiliarias'] = '|'.join(an)
    b['itens_imovel'] = b['itens_imovel'].replace('|area de servico', '')
w = csv.DictWriter(open('base_aptos.csv', 'w', encoding='utf-8', newline=''), fieldnames=list(base[0].keys()), delimiter=';', lineterminator='\n')
w.writeheader(); w.writerows(base)
print('base', len(base), 'links', len(links))
