#!/usr/bin/env python3
"""Filtro v2 (aprovado em 2026-11-28) e colunas novas da base.

Uso:
  python3 scripts/v2.py seed     arquiva a base atual em v1/ e monta a base v2 com quem passa no filtro
  python3 scripts/v2.py filtra   reaplica o filtro e as colunas novas na base atual (rodar depois de cada ingest)
"""
import csv, os, re, shutil, sys, unicodedata

BASE, LINKS, DESC = 'base_aptos.csv', 'links_aptos.csv', 'descricoes_aptos.csv'
NOVAS = ['sala_ampla', 'ar_condicionado', 'contas_individualizadas',
         'armarios_cozinha', 'armarios_banheiro', 'armarios_quartos']
TETO_MIN, TETO_MAX, AREA_MIN, QUARTOS_MIN = 4300, 7350, 68, 2
CONDO_MIN_SUPOSTO, ALUGUEL_MIN_SEM_CONDO = 600, 3300
TIPOS_OK = {'apartamento', 'cobertura', 'duplex', 'garden', 'apartamento duplex', 'apartamento garden'}
BAIRROS_V2 = ['vila mascote', 'jardim marajoara', 'vila alexandria', 'jardim prudencia', 'vila sofia',
              'campo belo', 'brooklin', 'brooklin paulista', 'brooklin novo', 'brooklin velho',
              'vila santa catarina', 'chacara santo antonio', 'granja julieta', 'alto da boa vista']


def sa(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').lower()


def num(x):
    try:
        return float(str(x).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def bairro_ok(b):
    return re.sub(r'\s+', ' ', sa(b)).strip() in BAIRROS_V2


def colunas_novas(r, desc):
    itens = sa(r.get('itens_imovel', ''))
    aus = sa(r.get('itens_ausentes', ''))
    t = sa(desc) + ' | ' + itens
    out = {}
    # sala ampla
    if re.search(r'(sala|living|estar)( de estar| de jantar)?( bem| muito)? (ampla|amplo|grande|espacos[ao])'
                 r'|(ampla|amplo|grande|espacosa) (sala|living)|sala (para|de|com) (2|3|dois|tres|02|03) ambientes'
                 r'|(2|3|dois|tres) ambientes', t):
        out['sala_ampla'] = 'sim'
    elif re.search(r'sala (compacta|pequena)', t):
        out['sala_ampla'] = 'nao'
    else:
        out['sala_ampla'] = ''
    # ar condicionado
    if re.search(r'(infra|infraestrutura|preparad\w*|ponto|pontos|tubulacao|espera)( \w+){0,3} (para |p/ )?(ar[ -]?condicionado|split)', t):
        ac = 'infra'
    else:
        ac = ''
    if re.search(r'(?<!infra para )(?<!infraestrutura para )\bar[ -]?condicionado|\bsplits?\b', t) and ac != 'infra':
        ac = 'sim'
    if not ac and re.search(r'sem ar[ -]?condicionado', aus + ' ' + t):
        ac = 'nao'
    out['ar_condicionado'] = ac
    # contas individualizadas (água e gás)
    if re.search(r'(agua|gas|hidrometro|medidor|medicao|consumo)( e (agua|gas|luz))?( \w+){0,2} individuali|'
                 r'(hidrometro|medidor|medicao) individual|relogio de (agua|gas) individual', t):
        out['contas_individualizadas'] = 'sim'
    elif re.search(r'(agua|gas)( e (agua|gas))? (inclus\w*|incluid\w*) no condominio|condominio (inclui|incluso|com) (agua|gas)'
                   r'|(agua|gas) (coletiv\w*|rateado)', t):
        out['contas_individualizadas'] = 'nao'
    else:
        out['contas_individualizadas'] = ''
    # armários
    def arm(rx_sim, rx_nao):
        if re.search(rx_nao, aus + ' | ' + t):
            return 'nao'
        if re.search(rx_sim, t):
            return 'sim'
        return ''
    out['armarios_cozinha'] = arm(
        r'armarios? (na |de |da )?cozinha|cozinha (toda |totalmente |com |bem )*(planejada|armarios|equipada|montada)'
        r'|armario cozinha|moveis planejados( na| da)? cozinha',
        r'sem armarios? na cozinha|cozinha sem armario')
    out['armarios_banheiro'] = arm(
        r'armarios? (no |nos |de |do |dos )?banheiros?|armario banheiro|gabinete|banheiros? (com armarios|planejados?)',
        r'sem armarios? no banheiro|banheiros? sem armario')
    out['armarios_quartos'] = arm(
        r'armarios? (no |nos |em |dos )?(quarto|dormitorio|suite)|armarios? embutidos?|armario quarto|closet'
        r'|(quartos|dormitorios|suite) (com armarios|planejad)|armarios em todos',
        r'sem armarios? no quarto|quartos? sem armario')
    if re.search(r'\bsem armarios?\b(?! n)', aus + ' | ' + t):
        for k in ('armarios_cozinha', 'armarios_banheiro', 'armarios_quartos'):
            out[k] = out[k] or 'nao'
    return out


def avalia(r):
    """Devolve (motivo_de_descarte ou None, lista de avisos)."""
    av = []
    tipo = sa(r['tipo'])
    if tipo not in TIPOS_OK:
        return f'tipo {r["tipo"]}', av
    if not bairro_ok(r['bairro']):
        return f'bairro {r["bairro"]}', av
    q = num(r['quartos'])
    if q is None or q < QUARTOS_MIN:
        return 'quartos', av
    s = num(r['suites'])
    if s is not None and s < 1:
        return 'sem suite', av
    if s is None:
        av.append('verificar suíte')
    a = num(r['area_util_m2'])
    if a is None or a < AREA_MIN:
        return 'area', av
    teto = sum(num(r[k]) or 0 for k in ('aluguel', 'condominio', 'iptu_mensal', 'seguro_incendio'))
    if num(r['condominio']) is None:
        # anúncio sem condomínio: supõe pelo menos R$ 600 de condomínio num prédio com lazer
        if teto + CONDO_MIN_SUPOSTO > TETO_MAX or (num(r['aluguel']) or 0) < ALUGUEL_MIN_SEM_CONDO:
            return f'valor {teto:.0f} sem condominio', av
    elif teto > TETO_MAX or teto < TETO_MIN:
        return f'valor {teto:.0f}', av
    bs = num(r['banheiros_sociais']) or num(r['banheiros'])
    if bs is None:
        av.append('verificar banheiros')
    elif bs < 2:
        return 'banheiros', av
    v = num(r['vagas'])
    if v is not None and v < 1:
        return 'sem vaga', av
    if v is None:
        av.append('verificar vaga')
    if r.get('area_servico') == 'nao':
        return 'sem area de servico', av
    if r.get('armarios_cozinha') == 'nao' or r.get('armarios_banheiro') == 'nao':
        return 'sem armarios cozinha/banheiro', av
    if not r.get('area_servico') and 'área de serviço' not in r['itens_imovel'] and 'lavanderia' not in r['itens_imovel']:
        av.append('verificar área de serviço')
    falta = [n for n, k in (('cozinha', 'armarios_cozinha'), ('banheiros', 'armarios_banheiro')) if r.get(k) != 'sim']
    if falta:
        av.append('verificar armários ' + ' e '.join(falta))
    return None, av


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=';'))


def save(p, rows, cols):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=';', lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})


AVISOS = ('verificar suíte', 'verificar banheiros', 'verificar vaga', 'verificar área de serviço',
          'verificar armários cozinha e banheiros', 'verificar armários cozinha', 'verificar armários banheiros')


def aplica(base, links, descs):
    dmap = {}
    for d in descs:
        dmap.setdefault(d['id_imovel'], []).append(d['descricao'])
    fica, sai = [], []
    for r in base:
        r.update(colunas_novas(r, ' | '.join(dmap.get(r['id'], []))))
        motivo, av = avalia(r)
        if motivo:
            sai.append(f"{r['id']} {motivo}")
            continue
        obs = [o for o in re.split(r'\.\s+', r['observacoes']) if o and o not in AVISOS]
        r['observacoes'] = '. '.join(obs + av)
        fica.append(r)
    ids = {r['id'] for r in fica}
    return fica, [l for l in links if l['id_imovel'] in ids], [d for d in descs if d['id_imovel'] in ids], sai


def main():
    cmd = sys.argv[1]
    if cmd == 'seed':
        os.makedirs('v1', exist_ok=True)
        for f in (BASE, LINKS, DESC, 'criterios.txt'):
            shutil.copy(f, f'v1/{f}')
    base, links, descs = load(BASE), load(LINKS), load(DESC)
    cols = list(base[0].keys())
    cols += [c for c in NOVAS if c not in cols]
    fica, lk, ds, sai = aplica(base, links, descs)
    save(BASE, fica, cols)
    save(LINKS, lk, list(links[0].keys()))
    save(DESC, ds, list(descs[0].keys()))
    print(f'base {len(fica)} (saíram {len(sai)}), links {len(lk)}, descrições {len(ds)}')
    if '-v' in sys.argv:
        print('; '.join(sai))


if __name__ == '__main__':
    main()
