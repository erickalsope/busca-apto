"""Gera uma cópia do site com a base embutida, para abrir sem internet ou sem servidor.

Uso: python3 scripts/site_offline.py [arquivo_de_saida]
Padrão de saída: busca-apto-offline.html na pasta atual.
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
saida = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("busca-apto-offline.html")


def ler(nome):
    arq = RAIZ / nome
    return arq.read_text(encoding="utf-8-sig").strip() if arq.exists() else ""


base, links, entorno = ler("base_aptos.csv"), ler("links_aptos.csv"), ler("entorno_aptos.csv")
for nome, texto in (("base", base), ("links", links), ("entorno", entorno)):
    if "</script" in texto.lower():
        sys.exit(f"O CSV {nome} tem um trecho que quebraria a página.")

pagina = (RAIZ / "site" / "index.html").read_text(encoding="utf-8")
pagina = (pagina.replace("__BASE_CSV__", base)
          .replace("__LINKS_CSV__", links)
          .replace("__ENTORNO_CSV__", entorno)
          .replace('<script src="config.js"></script>\n', ""))
saida.write_text(pagina, encoding="utf-8")
print(f"{saida} gerado com {base.count(chr(10))} imóveis.")
