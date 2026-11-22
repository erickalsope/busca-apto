#!/usr/bin/env python3
"""Converte o lote bruto do ZAP/VivaReal para o formato do process_qa e processa.
Formato bruto: id§tipo§endereco completo§aluguel§condominio§iptu§tipo_iptu§area§quartos§banheiros§vagas§andar§suites§mobiliado§pet§itens§qtd_fotos§foto§anunciante§codigo_anunciante§link
Uso: python3 scripts/process_zap.py raw/arquivo.txt AAAA-MM-DD limite [fonte]
"""
import re, sys, subprocess, os
LAZER = re.compile(r'piscina|academia|playground|sal[ãa]o de (festas|jogos)|churrasqueira|quadra|sauna|elevador|portaria|brinquedoteca|espa[çc]o gourmet|seguran[çc]a 24|condom[íi]nio fechado|spa|sal[ãa]o|pista|bicicletário|coworking|lavanderia coletiva|gerador|piquenique|cinema', re.I)
TIPOS = {'apartamento': 'Apartamento', 'casa': 'Casa', 'casa-de-condominio': 'CasaCondominio',
         'studio': 'StudioOuKitchenette', 'kitnet': 'StudioOuKitchenette', 'cobertura': 'Apartamento',
         'flat': 'StudioOuKitchenette', 'sobrado': 'Casa', 'sobrados': 'Casa', 'predio': 'Prédio inteiro'}
raw, hoje, limite = sys.argv[1], sys.argv[2], sys.argv[3]
fonte = sys.argv[4] if len(sys.argv) > 4 else 'ZAP Imóveis'
out = []
for line in open(raw, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line or line.startswith('#'):
        continue
    (zid, tp, addr, rent, condo, iptu, itype, area, beds, baths, park, andar, suites, furn, pets,
     itens, nfot, foto, adv, cod, link) = line.split('§')[:21]
    m = re.match(r'(.*?)\s+-\s+([^,]+),', addr)
    rua, bairro = (m.group(1), m.group(2)) if m else (addr, '')
    feats = [x for x in itens.split('|') if x]
    for slugf in re.findall(r'-com-([a-z\-]+?)-(?:campo|brooklin|vila|jardim|santo|alto|chacara|granja|socorro|interlagos|\d+m2)', link):
        f2 = slugf.replace('-', ' ')
        if f2 not in feats and LAZER.search(f2):
            feats.append(f2)
    if foto.startswith('V/'):
        foto = 'https://resizedimgs.vivareal.com.br/img/vr-listing/' + foto[2:]
    if foto.startswith('R/'):
        foto = 'https://resizedimgs.zapimoveis.com.br/img/vr-listing/' + foto[2:]
    if link.startswith('/'):
        link = ('https://www.vivareal.com.br' if 'Viva' in fonte else 'https://www.zapimoveis.com.br') + link
    lazer = '|'.join(x for x in feats if LAZER.search(x))
    imovel = '|'.join(x for x in feats if not LAZER.search(x))
    ctype = 'Normal' if condo != '' else 'NaoInformado'
    if iptu == '':
        itype = 'NaoInformado'
    out.append('§'.join([zid, TIPOS.get(tp, tp.capitalize()), rua, bairro, rent, condo or '0', ctype,
                         iptu or '0', itype, '', '', '', area, beds, suites, baths, park, andar,
                         furn, pets, imovel, lazer, nfot, foto, 'publicado', adv, fonte, link, cod]))
tmp = raw + '.conv'
open(tmp, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'process_qa.py'), tmp, hoje, limite], check=True)
os.remove(tmp)
