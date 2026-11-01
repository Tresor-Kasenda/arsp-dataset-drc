"""Déduplique les entreprises ARSP.

Une même entreprise apparaît plusieurs fois (ré-enregistrement / renouvellement). On regroupe
uniquement sur des preuves croisées pour ne PAS fusionner deux sociétés distinctes :

  R1  même RCCM  ET même n° d'impôt
  R2  même RCCM  ET noms similaires
  R3  même n° d'impôt ET noms similaires
  R4  même nom exact (normalisé) ET (même RCCM OU même n° d'impôt)

Un RCCM / n° d'impôt / n° ARSP partagé avec des noms différents est une erreur de saisie
probable : on ne fusionne pas, on signale (`possible_duplicate_of`).
Un même nom avec RCCM ET impôt différents est signalé aussi mais non fusionné.

Entrée  : data/arsp_subcontractors_sectors.csv
Sorties : data/arsp_subcontractors_dedup.csv   une ligne par entreprise (enregistrement le plus récent)
          data/duplicate_clusters.csv           détail des clusters fusionnés
"""
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

LEGAL = r"\b(SARLU|SARL|SAS|SASU|SA|SPRL|SCS|SNC|ETS|ETABLISSEMENTS?|STE|SOCIETE|ENTREPRISE|GROUPE|GROUP|DRC|RDC|CONGO|THE|LA|LE|LES|DES|DE|DU|ET|AND)\b"


def norm_name(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core_name(s):
    return re.sub(r"\s+", " ", re.sub(LEGAL, " ", norm_name(s))).strip()


def norm_rccm(s):
    s = re.sub(r"[^A-Z0-9]", "", s.upper())
    # CD/ISIRO/RCCM/13-B-1016/2019 -> ignore le suffixe /année
    return re.sub(r"(RCCM\d{2}[A-Z]\d+)\d{4}$", r"\1", s) if len(s) > 22 else s


def similar(a, b, thr=0.86):
    if not a or not b:
        return False
    return a == b or SequenceMatcher(None, a, b).ratio() >= thr


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def main(src="data/arsp_subcontractors_sectors.csv", dst="data/arsp_subcontractors_dedup.csv"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    n = len(rows)
    for r in rows:
        r["_name"], r["_core"] = norm_name(r["denomination"]), core_name(r["denomination"])
        r["_rccm"], r["_imp"] = norm_rccm(r["rccm"]), r["num_impot"].upper().strip()
    uf, reason = UF(n), {}

    def link(i, j, why):
        uf.union(i, j)
        reason.setdefault(i, why)
        reason.setdefault(j, why)

    by_rccm, by_imp, by_name = defaultdict(list), defaultdict(list), defaultdict(list)
    for i, r in enumerate(rows):
        if r["_rccm"]: by_rccm[r["_rccm"]].append(i)
        if r["_imp"]: by_imp[r["_imp"]].append(i)
        if r["_name"]: by_name[r["_name"]].append(i)

    def pairs(g):
        for k, idx in g.items():
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    yield idx[a], idx[b]

    for i, j in pairs(by_rccm):
        a, b = rows[i], rows[j]
        if a["_imp"] and a["_imp"] == b["_imp"]:
            link(i, j, "R1 rccm+impot")
        elif similar(a["_core"], b["_core"]):
            link(i, j, "R2 rccm+nom")
    for i, j in pairs(by_imp):
        if similar(rows[i]["_core"], rows[j]["_core"]):
            link(i, j, "R3 impot+nom")
    for i, j in pairs(by_name):
        a, b = rows[i], rows[j]
        if (a["_rccm"] and a["_rccm"] == b["_rccm"]) or (a["_imp"] and a["_imp"] == b["_imp"]):
            link(i, j, "R4 nom+identifiant")

    clusters = defaultdict(list)
    for i in range(n):
        clusters[uf.find(i)].append(i)

    # Collisions non fusionnées -> signalement
    flag = defaultdict(set)
    for g in (by_rccm, by_imp, by_name):
        for idx in g.values():
            for i in idx:
                for j in idx:
                    if i != j and uf.find(i) != uf.find(j):
                        flag[i].add(rows[j]["id"])
    for ident in ("num_ariane", "num_serie"):
        g = defaultdict(list)
        for i, r in enumerate(rows):
            if r[ident]: g[r[ident]].append(i)
        for idx in g.values():
            for i in idx:
                for j in idx:
                    if i != j and uf.find(i) != uf.find(j):
                        flag[i].add(rows[j]["id"])

    out, detail = [], []
    for cid, idx in clusters.items():
        idx.sort(key=lambda i: (rows[i]["created_at"], int(rows[i]["id"])))
        keep = rows[idx[-1]]  # enregistrement le plus récent = le plus à jour
        rec = {k: v for k, v in keep.items() if not k.startswith("_")}
        rec["n_records"] = len(idx)
        rec["all_ids"] = ";".join(rows[i]["id"] for i in idx)
        rec["first_registered"] = rows[idx[0]]["created_at"][:10]
        rec["last_registered"] = keep["created_at"][:10]
        rec["possible_duplicate_of"] = ";".join(sorted(flag.get(idx[-1], set()), key=int))
        out.append(rec)
        if len(idx) > 1:
            for i in idx:
                detail.append({"cluster_keep_id": keep["id"], "id": rows[i]["id"], "rule": reason.get(i, ""),
                               "denomination": rows[i]["denomination"], "rccm": rows[i]["rccm"],
                               "num_impot": rows[i]["num_impot"], "created_at": rows[i]["created_at"],
                               "kept": rows[i]["id"] == keep["id"]})
    out.sort(key=lambda r: int(r["id"]))
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    detail.sort(key=lambda r: (int(r["cluster_keep_id"]), r["created_at"]))
    with open("data/duplicate_clusters.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(detail[0].keys()))
        w.writeheader(); w.writerows(detail)
    merged = sum(1 for o in out if o["n_records"] > 1)
    print(f"{n} lignes -> {len(out)} entreprises uniques ({n-len(out)} doublons fusionnés, {merged} clusters)")
    print(f"{sum(1 for o in out if o['possible_duplicate_of'])} entreprises avec doublon possible non fusionné")


if __name__ == "__main__":
    main(*sys.argv[1:3])
