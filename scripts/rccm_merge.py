"""Aplatit les annonces RCCM, les classe par secteur et les rapproche du dataset ARSP.

Entrées : data/rccm/annonces.jsonl            (scripts/rccm_collect.py)
          data/arsp_subcontractors_segmented.csv
Sorties : data/rccm_companies.csv/.jsonl      toutes les sociétés du flux (secteur normalisé, province déduite)
          data/arsp_subcontractors_rccm.csv   dataset ARSP + colonnes rccm_* (idnat, ohada, activité, objet social…)
          data/rccm/match_report.md

Rapprochement : clé RCCM normalisée (ressort, année, A/B, numéro sans zéros).
  rccm_exact      ressort + année + type + numéro identiques
  rccm_loose_name même année/type/numéro, ressort différent, MAIS nom similaire
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dedupe import core_name, similar  # noqa: E402
from sectors import GENERIC, classify  # noqa: E402

RX = re.compile(r"RCCM\W*(\d{2})\W*([AB])\W*0*(\d+)")


def rccm_key(s):
    t = re.sub(r"\s+", "", (s or "").upper())
    m = RX.search(t)
    if not m:
        return None
    ress = re.sub(r"[^A-Z]", "", t.split("/RCCM")[0].replace("CD/", "", 1)) if "/RCCM" in t else ""
    return ress, m.group(1), m.group(2), str(int(m.group(3)))


def flatten(a):
    v = lambda k: (a.get(k) or {}).get("value", "") if isinstance(a.get(k), dict) else (a.get(k) or "")
    c = lambda k: (a.get(k) or {}).get("code", "") if isinstance(a.get(k), dict) else ""
    key = rccm_key(a.get("rccm"))
    row = {
        "rccm_id": a["_id"], "denomination": (a.get("denominationSociale") or a.get("_name") or "").strip(),
        "rccm": a.get("rccm", ""), "rccm_ohada": a.get("rccmOhada", ""), "idnat": a.get("numeroIdNat", ""),
        "forme_juridique": v("formeJuridiqueN3") or v("formeJuridiqueN2"), "forme_juridique_code": c("formeJuridiqueN3"),
        "secteur_ohada": v("secteurActiviteOHADA"), "secteur_ohada_code": c("secteurActiviteOHADA"),
        "activite_principale": v("activitePrincipaleOHADA"), "activite_code": c("activitePrincipaleOHADA"),
        "date_immatriculation": a.get("dateImmatriculationRCCM", ""), "objet_social": (a.get("objetSocial") or "").strip(),
        "capital_social": a.get("capitalSocial", ""), "ressort": key[0] if key else "",
        "rccm_url": f"https://rccm.cd/annonce?id={a['_id']}",
    }
    cats = classify(f"{row['activite_principale']} {row['secteur_ohada']}")
    src = "rccm_activite"
    if not cats:
        cats, src = [x for x in classify(row["objet_social"][:300]) if x not in GENERIC], "rccm_objet_social"
    row["sector_primary"] = cats[0] if cats else "Non précisé"
    row["sectors"] = ";".join(cats) if cats else "Non précisé"
    row["sector_source"] = src if cats else "none"
    return row


def province_by_ressort(arsp):
    c = defaultdict(Counter)
    for r in arsp:
        k = rccm_key(r["rccm"])
        if k and k[0] and r["province"]:
            c[k[0]][r["province"]] += 1
    out = {}
    for ress, cnt in c.items():
        prov, n = cnt.most_common(1)[0]
        if n >= 5 and n / sum(cnt.values()) >= 0.8:
            out[ress] = prov
    return out


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main(feed="data/rccm/annonces.jsonl", arsp_path="data/arsp_subcontractors_segmented.csv"):
    if not Path(feed).exists():
        sys.exit(f"{feed} introuvable : lancez d'abord scripts/rccm_collect.py")
    rows = [flatten(json.loads(l)) for l in open(feed, encoding="utf-8") if l.strip()]
    arsp = list(csv.DictReader(open(arsp_path, encoding="utf-8-sig")))
    prov = province_by_ressort(arsp)
    for r in rows:
        r["province"] = prov.get(r["ressort"], "")
    write_csv("data/rccm_companies.csv", rows)
    with open("data/rccm_companies.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    full, loose = {}, defaultdict(list)
    for r in rows:
        k = rccm_key(r["rccm"])
        if k:
            full[k] = r
            loose[k[1:]].append(r)
    add = ["rccm_match", "rccm_id", "rccm_url", "idnat", "rccm_ohada", "forme_juridique", "secteur_ohada", "activite_principale",
           "activite_code", "date_immatriculation", "objet_social", "rccm_sector_primary"]
    stats = Counter()
    for a in arsp:
        k, hit, how = rccm_key(a["rccm"]), None, ""
        if k and k in full:
            hit, how = full[k], "rccm_exact"
        elif k:
            cands = [c for c in loose.get(k[1:], []) if similar(core_name(c["denomination"]), core_name(a["denomination"]))]
            if len(cands) == 1:
                hit, how = cands[0], "rccm_loose_name"
        stats[how or "no_match"] += 1
        for col in add:
            a[col] = ""
        if hit:
            a.update(rccm_match=how, rccm_id=hit["rccm_id"], rccm_url=hit["rccm_url"], idnat=hit["idnat"], rccm_ohada=hit["rccm_ohada"],
                     forme_juridique=hit["forme_juridique"], secteur_ohada=hit["secteur_ohada"],
                     activite_principale=hit["activite_principale"], activite_code=hit["activite_code"],
                     date_immatriculation=hit["date_immatriculation"], objet_social=hit["objet_social"],
                     rccm_sector_primary=hit["sector_primary"])
    write_csv("data/arsp_subcontractors_rccm.csv", arsp)
    gain = sum(1 for a in arsp if a["sector_primary"] == "Non précisé" and a["rccm_sector_primary"] not in ("", "Non précisé"))
    rep = (f"# Rapprochement RCCM ↔ ARSP\n\n- Annonces RCCM : {len(rows)}\n- Entreprises ARSP : {len(arsp)}\n"
           + "".join(f"- {k} : {v}\n" for k, v in stats.most_common())
           + f"- Secteurs « Non précisé » ARSP désormais renseignés via le RCCM : {gain}\n"
           + f"- Provinces déduites pour {sum(1 for r in rows if r['province'])}/{len(rows)} sociétés RCCM\n")
    Path("data/rccm/match_report.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main(*sys.argv[1:3])
