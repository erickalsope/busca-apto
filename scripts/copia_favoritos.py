"""Copia favoritos, notas e descartes do Supabase para a pasta backup/ em CSV.

Roda todo dia pelo GitHub Actions (.github/workflows/copia-favoritos.yml).
Usa os segredos SUPABASE_URL e SUPABASE_SECRET_KEY do repositório.
Sem os segredos, avisa e termina sem erro.
"""
import csv
import json
import os
import pathlib
import sys
import urllib.request

URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
CHAVE = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
if not URL or not CHAVE:
    print("Segredos SUPABASE_URL e SUPABASE_SECRET_KEY ainda não configurados. Nada a copiar.")
    sys.exit(0)

CABECALHOS = {"apikey": CHAVE}
if not CHAVE.startswith("sb_"):
    # chave antiga no formato JWT (service_role) também vai no Authorization
    CABECALHOS["Authorization"] = "Bearer " + CHAVE


def ler(tabela, ordem):
    pedido = urllib.request.Request(f"{URL}/rest/v1/{tabela}?select=*&order={ordem}", headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return json.load(resposta)


def gravar(nome, campos, linhas):
    with open(PASTA / nome, "w", encoding="utf-8", newline="") as arq:
        escritor = csv.writer(arq, delimiter=";")
        escritor.writerow(campos)
        escritor.writerows(linhas)


PASTA = pathlib.Path("backup")
PASTA.mkdir(exist_ok=True)

membros = {m["usuario"]: m["nome"] for m in ler("membros", "nome")}
favoritos = ler("favoritos", "id_imovel")
notas = ler("notas", "id_imovel")
descartes = ler("descartes", "id_imovel")

gravar("favoritos.csv", ["id_imovel", "quem", "criado_em"],
       [[f["id_imovel"], membros.get(f["usuario"], f["usuario"]), f["criado_em"][:19]] for f in favoritos])
gravar("notas.csv", ["id_imovel", "texto", "quem", "atualizado_em"],
       [[n["id_imovel"], n["texto"].replace("\r", " ").replace("\n", " "),
         membros.get(n["atualizado_por"], ""), n["atualizado_em"][:19]] for n in notas])
gravar("descartes.csv", ["id_imovel", "quem", "criado_em"],
       [[d["id_imovel"], membros.get(d["descartado_por"], ""), d["criado_em"][:19]] for d in descartes])

print(f"{len(favoritos)} favoritos, {len(notas)} notas e {len(descartes)} descartes copiados.")
