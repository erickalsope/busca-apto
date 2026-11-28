#!/usr/bin/env python3
"""Recebe o JSON salvo pelo navegador ({lines, enr}), grava os lotes brutos e processa.
Uso: python3 scripts/ingest.py arquivo.json nome AAAA-MM-DD limite
"""
import json, sys, subprocess, glob, os
arq, nome, hoje, limite = sys.argv[1:5]
d = json.load(open(arq, encoding='utf-8'))
open(f'raw/{nome}.txt', 'w', encoding='utf-8').write('\n'.join(d.get('lines', [])) + '\n')
json.dump(d.get('enr', []), open(f'raw/enrich_{nome}.json', 'w', encoding='utf-8'), ensure_ascii=False)
subprocess.run([sys.executable, 'scripts/process_qa.py', f'raw/{nome}.txt', hoje, limite], check=True)
subprocess.run([sys.executable, 'scripts/finalize.py'], check=True)
ordem = ['quintoandar', 'lopes', 'zap', 'imovelweb', 'prohabitar']
files = [f'raw/enrich_{o}.json' for o in ordem] + sorted(f for f in glob.glob('raw/enrich_*.json')
                                                          if os.path.basename(f)[7:-5] not in ordem)
subprocess.run([sys.executable, 'scripts/enrich.py', hoje] + files, check=True)
subprocess.run([sys.executable, 'scripts/v2.py', 'filtra'], check=True)
