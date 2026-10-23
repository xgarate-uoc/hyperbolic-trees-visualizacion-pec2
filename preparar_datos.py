"""Convierte «Situació geogràfica dels ens locals de Catalunya» (dades obertes, ehvx-5ty7)
en el árbol del hyperbolic tree: Catalunya > vegueria > comarca > municipi.

Uso: python3 preparar_datos.py Situacio_geografica_dels_ens_locals_de_Catalunya.csv
Salida: arbol.js
"""
import json
import sys
import unicodedata

import pandas as pd


def clave(texto: str) -> str:
    """Orden alfabético que ignora acentos, artículos y mayúsculas."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    for art in ("l'", "el ", "la ", "els ", "les "):
        if t.startswith(art):
            t = t[len(art):]
    return t


df = pd.read_csv(sys.argv[1], dtype={"CODI_5": str})
anyo = int(df["ANUALITAT"].max())
mun = df[(df["TIPUS_ENS"] == "Municipis") & (df["ANUALITAT"] == anyo)].copy()
mun["POBLACIO"] = pd.to_numeric(mun["POBLACIO"]).astype(int)
assert len(mun) == mun["CODI_5"].nunique()

# Nodo: [nombre, nivel, índice del padre, código, población (solo municipios)]
nodos = [["Catalunya", 0, -1, "CAT", None]]
idx_veg, idx_com = {}, {}
for veg in sorted(mun["VEGUERIA"].unique(), key=clave):
    idx_veg[veg] = len(nodos)
    nodos.append([veg, 1, 0, f"V{mun.loc[mun.VEGUERIA == veg, 'CODI_VEGUERIA'].iloc[0]}", None])

# Una comarca cuelga de una sola vegueria, salvo l'Anoia: sus 8 municipios de l'Alta Segarra
# pertenecen a la vegueria Catalunya Central. Se crea un nodo de comarca por cada par vegueria-comarca.
pares = mun[["VEGUERIA", "COMARCA"]].drop_duplicates()
divididas = set(pares["COMARCA"][pares["COMARCA"].duplicated(keep=False)])
for veg, com in sorted(pares.itertuples(index=False), key=lambda p: (clave(p[0]), clave(p[1]))):
    nombre = com
    if com in divididas:
        nombre = f"{com} (Alta Segarra)" if veg == "Catalunya Central" else com
    idx_com[(veg, com)] = len(nodos)
    nodos.append([nombre, 2, idx_veg[veg], "C" + com, None])

for r in sorted(mun.itertuples(index=False), key=lambda r: (clave(r.VEGUERIA), clave(r.COMARCA), clave(r.NOM_ARTICLE))):
    nodos.append([r.NOM_ARTICLE, 3, idx_com[(r.VEGUERIA, r.COMARCA)], r.CODI_5, int(r.POBLACIO)])

salida = {
    "fuente": "Generalitat de Catalunya, Dades Obertes: «Situació geogràfica dels ens locals de Catalunya» (ehvx-5ty7)",
    "anyo_poblacion": anyo,
    "nodos": nodos,
}
# Se guarda como JavaScript (window.ARBOL = ...) para que index.html funcione también en local con doble clic
with open("arbol.js", "w", encoding="utf-8") as f:
    f.write("window.ARBOL = " + json.dumps(salida, ensure_ascii=False, separators=(",", ":")) + ";\n")

# Resumen para el guion
total = mun["POBLACIO"].sum()
print(f"Año {anyo}. Nodos: {len(nodos)} = 1 + {len(idx_veg)} vegueries + {len(idx_com)} comarques + {len(mun)} municipis")
print(f"Población total: {total:,}")
cortes = [0, 500, 2000, 10000, float("inf")]
mun["clase"] = pd.cut(mun["POBLACIO"], cortes, right=False, labels=["<500", "500-1.999", "2.000-9.999", ">=10.000"])
res = mun.groupby("clase", observed=True)["POBLACIO"].agg(["size", "sum"])
res["% municipios"] = (res["size"] / len(mun) * 100).round(1)
res["% población"] = (res["sum"] / total * 100).round(1)
print(res)
veg = mun.groupby("VEGUERIA").agg(municipios=("CODI_5", "size"), poblacion=("POBLACIO", "sum"),
                                  menos_500=("POBLACIO", lambda s: round((s < 500).mean() * 100, 1)))
veg["% población"] = (veg["poblacion"] / total * 100).round(1)
print(veg.sort_values("municipios", ascending=False))
