#!/usr/bin/env python3
"""Converte o lote bruto do Imovelweb para o formato do process_qa e processa.
Formato bruto: id§tipo§endereco§bairro§aluguel§condominio§iptu§area_util§area_total§quartos§banheiros§vagas§suites§andar§mobiliado§pet§itens§lazer§qtd_fotos§foto§anunciante§codigo§link
Uso: python3 scripts/process_iw.py raw/arquivo.txt AAAA-MM-DD limite
"""
import re, sys, subprocess, os
TIPOS = {'apartamento': 'Apartamento', 'casa': 'Casa', 'sobrado': 'Casa', 'cobertura': 'Apartamento',
         'kitnet': 'StudioOuKitchenette', 'studio': 'StudioOuKitchenette', 'flat': 'StudioOuKitchenette'}
raw, hoje, limite = sys.argv[1:4]
out = []
for line in open(raw, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line or line.startswith('#'):
        continue
    f = line.split('§')
    (iid, tp, loc, bairro, rent, condo, iptu, util, tot, beds, baths, park, suites, andar, mob, pet,
     itens, lazer, nfot, foto, adv, cod, link) = f[:23]
    link = link.split('?')[0]
    rua = re.split(r',\s*(?:' + re.escape(bairro) + r'|São Paulo)', loc)[0].strip() if loc else ''
    area = util or tot
    itype = 'Normal' if iptu else 'NaoInformado'
    extra = []
    if not util and tot:
        extra.append('área total, verificar área útil')
    if iptu and rent and float(iptu) > 0.25 * float(rent):
        itype = 'Anual'
        extra.append('iptu parecia anual e foi dividido por 12, verificar')
    elif iptu:
        extra.append('verificar se o iptu do Imovelweb é mensal')
    out.append('§'.join([iid, TIPOS.get(tp, tp.capitalize()), rua, bairro, rent, condo or '0',
                         'Normal' if condo else 'NaoInformado', iptu or '0', itype, '', '', '', area, beds,
                         suites, baths, park, andar, mob, pet, itens, lazer, nfot, foto, 'publicado',
                         adv, 'Imovelweb', 'https://www.imovelweb.com.br' + link if link.startswith('/') else link,
                         cod, '. '.join(extra)]))
tmp = raw + '.conv'
open(tmp, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
if os.environ.get('CONVERT_ONLY'):
    print(tmp)
    sys.exit(0)
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'process_qa.py'), tmp, hoje, limite], check=True)
os.remove(tmp)
