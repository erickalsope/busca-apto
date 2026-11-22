#!/usr/bin/env python3
"""Processa um lote bruto do QuintoAndar (campos separados por §) e atualiza os CSVs.
Uso: python3 scripts/process_qa.py raw/arquivo.txt AAAA-MM-DD [limite_total]
"""
import csv, json, sys, os

BASE = 'base_aptos.csv'
LINKS = 'links_aptos.csv'
BASE_COLS = 'id;status;data_primeira_coleta;data_ultima_verificacao;data_indisponivel;qtd_anuncios;imobiliarias;link_principal;foto_capa_url;tipo;bairro;endereco;aluguel;condominio;iptu_mensal;total_mensal;outras_taxas;area_util_m2;valor_m2;quartos;suites;banheiros;vagas;andar;mobiliado;aceita_pet;itens_imovel;lazer_condominio;qtd_fotos;observacoes'.split(';')
LINK_COLS = 'id_imovel;fonte;anunciante;codigo_anunciante;link;aluguel_anunciado;status_link;data_primeira_coleta;data_ultima_verificacao'.split(';')
ACESS = {'corrimão', 'piso tátil', 'rampas de acesso', 'vaga de garagem acessível',
         'quartos e corredores com portas amplas', 'banheiro adaptado'}
TIPOS = {'Apartamento': 'apartamento', 'Casa': 'casa', 'CasaCondominio': 'casa em condomínio',
         'StudioOuKitchenette': 'studio'}
BAIRROS_OK = {'brooklin', 'brooklin paulista', 'brooklin novo', 'campo belo', 'vila mascote',
              'jardim prudência', 'santo amaro', 'alto da boa vista', 'chácara santo antônio',
              'granja julieta', 'jardim marajoara', 'socorro', 'interlagos'}


def load(path, cols):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def save(path, cols, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';', lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})


def num(x):
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return ''
    return str(int(v)) if float(v).is_integer() else f'{v:.2f}'


def lst(s):
    out = []
    for it in s.split('|'):
        it = it.strip().replace('portaria_24h', 'portaria 24h')
        if it and it not in ACESS and it not in out:
            out.append(it)
    return '|'.join(out)


def norm(s):
    import re
    s = (s or '').strip().lower().replace('av. ver.', 'avenida vereador').replace('av. ', 'avenida ')
    return re.sub(r'\s*(,\s*\d+.*|-\s.*)$', '', s).strip()


def main():
    raw, hoje = sys.argv[1], sys.argv[2]
    limite = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    base = load(BASE, BASE_COLS)
    links = load(LINKS, LINK_COLS)
    by_link = {l['link']: l for l in links}
    st = dict(lidos=0, novos=0, dup=0, ja=0, desc=0, erro=0)
    desc_motivos = []
    for line in open(raw, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#') or line.startswith('CNT'):
            continue
        f = line.split('§')
        st['lidos'] += 1
        if len(f) < 26 or f[1] == 'ERRO' or not f[2]:
            st['erro'] += 1
            continue
        (qid, tipo, rua, bairro, rent, condo, ctype, iptu, itype, seg, taxa, tsite, area, beds,
         suites, baths, park, floor, furn, pets, amen, inst, nfot, og, status, pub) = f[:26]
        fonte, link, codigo = (f[26], f[27], f[28]) if len(f) >= 29 else ('QuintoAndar', f'https://www.quintoandar.com.br/imovel/{qid}', qid)
        if link in by_link:
            by_link[link]['data_ultima_verificacao'] = hoje
            st['ja'] += 1
            continue
        rent, condo, iptu, seg, taxa, area = map(num, (rent, condo, iptu, seg, taxa, area))
        beds_n = num(beds)
        obs = []
        if ctype == 'IncluidoNoAluguel':
            condo = 0.0
            obs.append('condomínio incluso no aluguel ou inexistente')
        elif ctype == 'NaoInformado':
            condo = None
            obs.append('verificar condominio')
        if itype == 'NaoInformado':
            iptu = None
            if fonte != 'QuintoAndar':
                pass
            obs.append('verificar iptu')
        elif itype == 'Anual':
            iptu = round(num(iptu) / 12, 2) if num(iptu) else None
            obs.append('iptu convertido de anual')
        elif itype == 'NaoExiste':
            iptu = 0.0
            obs.append('iptu inexistente segundo o anúncio')
        elif itype == 'Isento':
            iptu = 0.0
            obs.append('iptu isento')
        elif itype and itype not in ('Normal',):
            obs.append(f'iptu tipo {itype}')
        teto = (rent or 0) + (condo or 0) + (iptu or 0) + (seg or 0)
        motivo = None
        if not rent:
            motivo = 'sem aluguel'
        elif beds_n is not None and beds_n < 2:
            motivo = 'quartos'
        elif area is not None and area < 60:
            motivo = 'area'
        elif teto > 8000 or teto < 3000:
            motivo = f'valor {teto:.0f}'
        elif norm(bairro) not in BAIRROS_OK:
            motivo = f'bairro {bairro}'
        if motivo:
            st['desc'] += 1
            desc_motivos.append(f'{qid} {motivo}')
            continue
        total = (rent or 0) + (condo or 0) + (iptu or 0)
        outras = (seg or 0) + (taxa or 0)
        if outras:
            obs.append(f'outras_taxas = seguro incêndio {fmt(seg)} + taxa de serviço {fmt(taxa)}')
        try:
            fl = json.loads(floor or '{}')
            andar = f"{fl['min']}-{fl['max']}" if isinstance(fl, dict) and 'min' in fl else (str(fl) if fl not in ({}, '') else '')
        except Exception:
            andar = floor or ''
        if andar and '-' in andar:
            obs.append(f'andar informado como faixa {andar}')
        foto = ('https://www.quintoandar.com.br' + og[1:]) if og.startswith('Q') else og
        import re as _re
        anunciante = _re.sub(r'\s*Creci.*$', '', pub).strip() or 'QuintoAndar'
        if fonte != 'QuintoAndar':
            obs.append(f'código no {fonte} {qid}')

        # dedupe
        match, parcial = None, None
        for b in base:
            if norm(b['bairro']) != norm(bairro) or norm(b['endereco']) != norm(rua):
                continue
            if b['quartos'] != fmt(beds_n):
                continue
            a2 = num(b['area_util_m2'])
            area_ok = a2 is not None and area is not None and abs(a2 - area) <= 3
            c2 = num(b['condominio'])
            cond_ok = (c2 is not None and condo is not None and
                       (abs(c2 - condo) <= 0.10 * max(c2, condo) or (c2 == 0 and condo == 0)))
            vag_ok = b['vagas'] == park
            and_ok = not b['andar'] or not andar or b['andar'] == andar
            if area_ok and cond_ok and vag_ok and and_ok:
                match = b
                break
            if area_ok and (cond_ok or vag_ok):
                parcial = parcial or b
        if match is None and len(base) >= limite:
            st['desc'] += 1
            desc_motivos.append(f'{qid} limite')
            continue
        lrow = dict(fonte=fonte, anunciante=anunciante, codigo_anunciante=codigo, link=link,
                    aluguel_anunciado=fmt(rent), status_link='ativo', data_primeira_coleta=hoje,
                    data_ultima_verificacao=hoje)
        if match is not None:
            lrow['id_imovel'] = match['id']
            links.append(lrow)
            by_link[link] = lrow
            st['dup'] += 1
            if num(match['aluguel']) is None or rent < num(match['aluguel']):
                match['aluguel'] = fmt(rent)
                match['link_principal'] = link
                match['total_mensal'] = fmt(num(match['aluguel']) + (num(match['condominio']) or 0) + (num(match['iptu_mensal']) or 0))
                match['valor_m2'] = f"{rent / num(match['area_util_m2']):.2f}" if num(match['area_util_m2']) else ''
            match['data_ultima_verificacao'] = hoje
            continue
        if parcial is not None:
            obs.append(f"possível duplicado do id {parcial['id']}")
        nid = str(max([int(b['id']) for b in base] + [0]) + 1)
        row = dict(id=nid, status='disponivel', data_primeira_coleta=hoje, data_ultima_verificacao=hoje,
                   data_indisponivel='', link_principal=link, foto_capa_url=foto,
                   tipo=TIPOS.get(tipo, tipo.lower()), bairro=bairro, endereco=rua,
                   aluguel=fmt(rent), condominio=fmt(condo), iptu_mensal=fmt(iptu), total_mensal=fmt(total),
                   outras_taxas=fmt(outras) if outras else '', area_util_m2=fmt(area),
                   valor_m2=f'{rent / area:.2f}' if area else '', quartos=fmt(beds_n),
                   suites=suites, banheiros=baths, vagas=park, andar=andar,
                   mobiliado='sim' if furn == 'true' else 'nao' if furn == 'false' else '',
                   aceita_pet='sim' if pets == 'true' else 'nao' if pets == 'false' else '',
                   itens_imovel=lst(amen), lazer_condominio=lst(inst),
                   qtd_fotos=nfot if nfot not in ('', '0') else '', observacoes='. '.join(obs))
        base.append(row)
        lrow['id_imovel'] = nid
        links.append(lrow)
        by_link[link] = lrow
        st['novos'] += 1

    # consolida qtd_anuncios, imobiliarias e data de verificação
    for b in base:
        ls = [l for l in links if l['id_imovel'] == b['id'] and l['status_link'] == 'ativo']
        b['qtd_anuncios'] = str(len(ls))
        anun = []
        for l in ls:
            if l['anunciante'] not in anun:
                anun.append(l['anunciante'])
        b['imobiliarias'] = '|'.join(anun)
        datas = [l['data_ultima_verificacao'] for l in links if l['id_imovel'] == b['id']]
        if datas:
            b['data_ultima_verificacao'] = max(datas)
    save(BASE, BASE_COLS, base)
    save(LINKS, LINK_COLS, links)
    print(json.dumps(st, ensure_ascii=False), 'base:', len(base), 'links:', len(links))
    if desc_motivos:
        print('descartes:', '; '.join(desc_motivos))


if __name__ == '__main__':
    main()
