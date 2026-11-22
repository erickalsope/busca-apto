#!/usr/bin/env python3
"""Preenche as colunas novas de base_aptos.csv e o descricoes_aptos.csv a partir dos JSON
extraídos no navegador (um objeto por anúncio).

Campos do JSON: link, fonte, codigo, ok, lat, lng, prec, cep, numero, desc, itens, ausentes,
seguro, taxa, banheiros, aluguel, andar.

Uso: python3 scripts/enrich.py AAAA-MM-DD [--commit-a-cada 30] arquivo1.json [arquivo2.json ...]
"""
import csv, json, re, sys, subprocess, unicodedata

BASE, LINKS, DESC = 'base_aptos.csv', 'links_aptos.csv', 'descricoes_aptos.csv'
NEW = ('latitude;longitude;localizacao_precisao;cep;numero;andar_exato;seguro_incendio;taxa_servico;'
       'banheiros_sociais;lavabo;banheiro_servico;vagas_cobertas;vagas_descobertas;aquecimento_agua;piso;'
       'cozinha;area_servico;seguranca;mercadinho;itens_ausentes').split(';')
LAZER_EXTRA = [('brinquedoteca', r'brinquedoteca'), ('espaço kids', r'espa[çc]o kids|kids'),
               ('piscina infantil', r'piscina infantil|piscina para crian[çc]as'),
               ('quadra', r'\bquadra'), ('área verde', r'[áa]rea verde'),
               ('mercadinho', r'minimercado|mini mercado|mercadinho|\bmarket\b|mercado aut[ôo]nomo')]


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').lower()


def num(x):
    try:
        return float(str(x).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None or v == '':
        return ''
    v = float(v)
    return str(int(v)) if v.is_integer() else f'{v:.2f}'


def classifica(r, base_row):
    desc = r.get('desc') or ''
    itens = [i.lower() for i in (r.get('itens') or []) if i]
    aus = [a.lower() for a in (r.get('ausentes') or []) if a]
    t = sem_acento(desc + ' | ' + ' | '.join(itens))
    ta = sem_acento(' | '.join(aus))
    out = {}
    # localização
    lat, lng = num(r.get('lat')), num(r.get('lng'))
    if lat and lng and -25 < lat < -22 and -48 < lng < -45:
        out['latitude'], out['longitude'] = str(r['lat']), str(r['lng'])
        out['localizacao_precisao'] = r.get('prec') or ''
    out['cep'] = r.get('cep') or ''
    out['numero'] = str(r.get('numero') or '')
    m = re.search(r'(\d{1,2})\s*(?:º|o|°|ª)?\s*andar', t)
    out['andar_exato'] = m.group(1) if m else (str(r['andar']) if r.get('andar') else '')
    out['seguro_incendio'] = fmt(r.get('seguro'))
    out['taxa_servico'] = fmt(r.get('taxa'))
    # banheiros
    lav = 'sim' if re.search(r'lavabo', t) else ('nao' if 'lavabo' in ta else '')
    bs = 'sim' if re.search(r'banheiro de (servico|empregad)|wc de (servico|empregad)|banheiro da empregada', t) else \
        ('nao' if re.search(r'banheiro de servico', ta) else '')
    out['lavabo'], out['banheiro_servico'] = lav, bs
    b = num(r.get('banheiros')) or num(base_row.get('banheiros'))
    if b:
        soc = b - (1 if lav == 'sim' else 0) - (1 if bs == 'sim' else 0)
        out['banheiros_sociais'] = fmt(max(soc, 1))
    # vagas
    vagas = num(base_row.get('vagas'))
    vc = re.search(r'(\d+)\s*vagas?\s*(de garagem\s*)?cobertas?', t)
    vd = re.search(r'(\d+)\s*vagas?\s*(de garagem\s*)?descobertas?', t)
    if vc or vd:
        out['vagas_cobertas'] = vc.group(1) if vc else ''
        out['vagas_descobertas'] = vd.group(1) if vd else ''
        if vagas and vc and not vd:
            out['vagas_descobertas'] = fmt(max(vagas - int(vc.group(1)), 0))
        if vagas and vd and not vc:
            out['vagas_cobertas'] = fmt(max(vagas - int(vd.group(1)), 0))
    elif vagas and re.search(r'vagas? (de garagem )?cobertas?|garagem coberta', t) and not re.search(r'descobert', t):
        out['vagas_cobertas'], out['vagas_descobertas'] = fmt(vagas), '0'
    elif vagas and re.search(r'vagas? (de garagem )?descobertas?', t) and not re.search(r'(?<!des)cobert', t):
        out['vagas_cobertas'], out['vagas_descobertas'] = '0', fmt(vagas)
    # aquecimento
    if re.search(r'aquecedor a gas|aquecimento a gas|aquecimento central|chuveiro a gas|aquecedor de passagem', t):
        out['aquecimento_agua'] = 'gas'
    elif re.search(r'aquec\w* solar', t):
        out['aquecimento_agua'] = 'solar'
    elif re.search(r'chuveiro eletrico|aquecimento eletrico|aquecedor eletrico', t):
        out['aquecimento_agua'] = 'eletrico'
    # piso
    pisos = []
    for nome, rx in [('madeira', r'piso de madeira|assoalho|tabua|piso de tacos? de madeira|madeira macica|piso madeira'),
                     ('taco', r'\btaco'), ('laminado', r'laminado'), ('vinilico', r'vinilico|vinil'),
                     ('porcelanato', r'porcelanato'), ('ceramica', r'ceramica'), ('carpete', r'carpete')]:
        if re.search(rx, t):
            pisos.append(nome)
    if 'taco' in pisos and 'madeira' in pisos:
        pisos.remove('madeira')
    out['piso'] = pisos[0] if len(pisos) == 1 else ('misto' if pisos else '')
    # cozinha e área de serviço
    if re.search(r'cozinha (bem )?(ampla|grande|espacosa)', t):
        out['cozinha'] = 'ampla'
    elif re.search(r'cozinha (compacta|pequena)', t):
        out['cozinha'] = 'compacta'
    elif re.search(r'cozinha', t):
        out['cozinha'] = 'normal'
    if re.search(r'(sem|nao (possui|tem)) area de servico', t) or 'area de servico' in ta:
        out['area_servico'] = 'nao'
    elif re.search(r'area de servico (bem )?(ampla|grande|espacosa)|cabe (maquina de )?lava.?loucas', t):
        out['area_servico'] = 'ampla'
    elif re.search(r'area de servico (compacta|pequena)', t):
        out['area_servico'] = 'compacta'
    elif re.search(r'area de servico|lavanderia', t):
        out['area_servico'] = 'normal'
    # segurança
    seg = []
    for nome, rx in [('portaria 24h', r'portaria 24|portaria_24h|portaria 24 horas'),
                     ('vigilancia', r'vigilan|vigia|guarita|seguranca 24|vigilante'),
                     ('cameras', r'camera|cftv|circuito (fechado|interno)'),
                     ('controle de acesso', r'controle de acesso|biometri|acesso por (tag|cartao)|reconhecimento facial'),
                     ('cerca eletrica', r'cerca eletrica'), ('alarme', r'alarme'),
                     ('rua com seguranca privada', r'seguranca (privada|particular) na rua|rua com seguranca'),
                     ('vila ou condominio fechado', r'condominio fechado|\bvila\b|rua fechada|rua sem saida')]:
        if re.search(rx, t):
            seg.append(nome)
    out['seguranca'] = '|'.join(seg)
    if re.search(r'minimercado|mini mercado|mercadinho|\bmarket\b|mercado autonomo', t):
        out['mercadinho'] = 'sim'
    elif re.search(r'minimercado|mercadinho|market', ta):
        out['mercadinho'] = 'nao'
    # itens ausentes
    ausentes = list(aus)
    for m in re.finditer(r'\bsem (varanda|elevador|vaga|garagem|armarios?|portaria|piscina|lazer|condominio|area de servico|sacada)', t):
        ausentes.append('sem ' + m.group(1))
    for m in re.finditer(r'nao (possui|tem|ha) (varanda|elevador|vaga|garagem|armarios?|portaria|piscina|lazer|area de servico|sacada)', t):
        ausentes.append('sem ' + m.group(2))
    vis = []
    for a in ausentes:
        if a not in vis:
            vis.append(a)
    out['itens_ausentes'] = '|'.join(vis)
    # lazer extra
    lz = [x for x in (base_row.get('lazer_condominio') or '').split('|') if x]
    for nome, rx in LAZER_EXTRA:
        if nome not in lz and re.search(rx, t) and not re.search(rx, ta):
            lz.append(nome)
    out['_lazer'] = '|'.join(lz)
    return out


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=';'))


def save(p, rows, cols):
    w = csv.DictWriter(open(p, 'w', encoding='utf-8', newline=''), fieldnames=cols, delimiter=';', lineterminator='\n')
    w.writeheader(); w.writerows(rows)


def main():
    args = sys.argv[1:]
    hoje = args.pop(0)
    passo = 0
    if args and args[0] == '--commit-a-cada':
        passo = int(args[1]); args = args[2:]
    raws = []
    for a in args:
        raws += json.load(open(a, encoding='utf-8'))
    por_link = {r['link'].split('?')[0].rstrip('/'): r for r in raws if r.get('link')}
    base, links, descs = load(BASE), load(LINKS), load(DESC)
    bcols = list(base[0].keys())
    dkey = {(d['fonte'], d['codigo_anunciante']): d for d in descs}
    feitos, fora, mudou, lote = 0, [], 0, 0
    for b in base:
        ls = [l for l in links if l['id_imovel'] == b['id']]
        ls.sort(key=lambda l: l['link'] != b['link_principal'])
        achou = False
        for l in ls:
            r = por_link.get(l['link'].split('?')[0].rstrip('/'))
            if not r:
                continue
            if r.get('ok') is False:
                fora.append(l['link']); continue
            if r.get('desc'):
                d = (r['desc'] or '').replace('\r', ' ').replace('\n', ' ').replace(';', ',')
                d = re.sub(r'\s+', ' ', d).strip()
                dkey[(l['fonte'], l['codigo_anunciante'])] = dict(id_imovel=b['id'], fonte=l['fonte'],
                                                                  codigo_anunciante=l['codigo_anunciante'], descricao=d)
            novo = num(r.get('aluguel'))
            if novo and num(l['aluguel_anunciado']) and abs(novo - num(l['aluguel_anunciado'])) > 0.5:
                l['aluguel_anunciado'] = fmt(novo); mudou += 1
                if l['link'] == b['link_principal']:
                    b['aluguel'] = fmt(novo)
                    b['total_mensal'] = fmt(novo + (num(b['condominio']) or 0) + (num(b['iptu_mensal']) or 0))
                    if num(b['area_util_m2']):
                        b['valor_m2'] = f"{novo / num(b['area_util_m2']):.2f}"
            l['data_ultima_verificacao'] = hoje
            out = classifica(r, b)
            lz = out.pop('_lazer')
            if not achou:
                for k, v in out.items():
                    b[k] = v
                b['lazer_condominio'] = lz
            else:
                for k, v in out.items():
                    if not b.get(k) and v:
                        b[k] = v
            achou = True
        if achou:
            b['data_ultima_verificacao'] = hoje
            feitos += 1; lote += 1
            if passo and lote >= passo:
                commit(base, bcols, links, dkey, lote, hoje)
                lote = 0
    commit(base, bcols, links, dkey, lote, hoje, push=bool(passo))
    print(json.dumps(dict(imoveis_atualizados=feitos, links_fora_do_ar=len(fora), precos_mudados=mudou)))
    if fora:
        print('fora do ar:', ' '.join(fora[:40]))


def commit(base, bcols, links, dkey, n, hoje, push=True):
    save(BASE, base, bcols)
    save(LINKS, links, list(links[0].keys()))
    save(DESC, sorted(dkey.values(), key=lambda d: int(d['id_imovel'])), ['id_imovel', 'fonte', 'codigo_anunciante', 'descricao'])
    if push and n:
        subprocess.run(['git', 'add', '-A'], check=True)
        msg = f'atualização {hoje}, colunas novas em {n} imóveis\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01FTRWjqJJGBEeq4B2ZB7Bbf'
        subprocess.run(['git', 'commit', '-qm', msg], check=True)
        subprocess.run(['git', '-c', 'push.negotiate=true', 'push', '-q', 'origin', 'main'], check=True)


if __name__ == '__main__':
    main()
