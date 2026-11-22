#!/usr/bin/env python3
"""Converte o lote bruto da Lopes para o formato do process_qa e processa.
Formato bruto: id§tipo§rua§bairro§aluguel§condominio§iptu§suites§banheiros§vagas§mobiliado§pet§itens§lazer§foto§anunciante
Complemento: raw/lopes_fix.txt com 'id quartos area' (área do anúncio).
Uso: python3 scripts/process_lopes.py raw/arquivo.txt raw/fix.txt AAAA-MM-DD limite
"""
import sys, subprocess, os
raw, fix, hoje, limite = sys.argv[1:5]
FIX = {l.split()[0]: l.split()[1:] for l in open(fix, encoding='utf-8') if l.strip()}
TIPOS = {'Apartamento': 'Apartamento', 'Casa': 'Casa', 'Casa térrea': 'Casa', 'Casa de vila': 'Casa',
         'Condomínio': 'CasaCondominio', 'Sobrado': 'Casa', 'Cobertura': 'Apartamento'}
BAIRRO = {'Chacara Santo Antonio': 'Chácara Santo Antônio', 'Jardim Prudencia': 'Jardim Prudência',
          'Alto Da Boa Vista': 'Alto da Boa Vista'}
out = []
for line in open(raw, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line or line.startswith('#'):
        continue
    (lid, tp, rua, bai, rent, condo, iptu, suites, baths, park, mob, pet, itens, lazer, foto, adv) = line.split('§')[:16]
    beds, area = (FIX.get(lid) + ['', ''])[:2] if lid in FIX else ('', '')
    extra = []
    if area and int(area) > 1000:
        extra.append(f'área informada {area} m² parece errada, verificar')
        area = ''
    if not area:
        extra.append('verificar area')
    foto_url = f'https://betaimages.lopes.com.br/realestate/sml/{lid}/{foto}' if foto else ''
    out.append('§'.join([lid, TIPOS.get(tp, tp), rua, BAIRRO.get(bai, bai), rent, condo or '0',
                         'Normal' if condo != '' else 'NaoInformado', iptu or '0',
                         'Normal' if iptu != '' else 'NaoInformado', '', '', '', area, beds, suites, baths,
                         park, '', mob, pet, itens, lazer, '', foto_url, 'publicado', adv, 'Lopes',
                         f'https://www.lopes.com.br/imovel/{lid}', lid, '. '.join(extra)]))
tmp = raw + '.conv'
open(tmp, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'process_qa.py'), tmp, hoje, limite], check=True)
os.remove(tmp)
