"""Classe les entreprises ARSP selon leur présence numérique (e-mail pro / site web).

Entrée  : data/arsp_subcontractors_enriched.csv
Sorties : data/arsp_subcontractors_segmented.csv      toutes les entreprises + colonnes email_type, segment…
          data/analysis/sans_site_ni_email_pro.csv    cible principale (segments A + B)
          data/analysis/segment_*.csv                 un fichier par segment
          data/analysis/stats_*.csv + RAPPORT.md      statistiques par secteur / province / taille

email_type : professional (domaine propre) | professional_shared (domaine partagé par >3 sociétés,
             ex. cabinet qui enregistre ses clients) | free | free_typo (gamail.com…) | missing
segment    : A  aucun e-mail
             B  e-mail gratuit uniquement (gmail, yahoo…), pas de site
             C  e-mail sur domaine partagé (cabinet/agence), pas de site propre
             D  e-mail pro / site candidat (low) à confirmer
             E  e-mail pro + site candidat fiable (high/medium)
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from websites import FREE, is_free  # noqa: E402

SEGMENTS = {
    "A": "A - Aucun e-mail",
    "B": "B - E-mail gratuit uniquement, sans site",
    "C": "C - E-mail sur domaine partagé (cabinet/agence), sans site propre",
    "D": "D - E-mail pro / site candidat peu fiable (low)",
    "E": "E - E-mail pro + site candidat (high/medium)",
}
LEGAL_FORM = re.compile(r"\b(SARLU|SARL|SASU|SAS|SPRL|SA|SCS|SNC|ETABLISSEMENTS?|ETS)\b")


def legal_form(name):
    m = LEGAL_FORM.search(name.upper().replace(".", ""))
    f = m.group(1) if m else "AUTRE"
    return {"ETABLISSEMENT": "ETS", "ETABLISSEMENTS": "ETS"}.get(f, f)


def write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(src="data/arsp_subcontractors_enriched.csv"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    by_dom = defaultdict(set)
    for r in rows:
        if "@" in r["email"]:
            by_dom[r["email"].split("@")[-1]].add(r["id"])

    for r in rows:
        dom = r["email"].split("@")[-1] if "@" in r["email"] else ""
        if not dom:
            et = "missing"
        elif dom in FREE:
            et = "free"
        elif is_free(dom):
            et = "free_typo"
        elif len(by_dom[dom]) > 3:
            et = "professional_shared"
        else:
            et = "professional"
        r["email_type"], r["email_domain"] = et, dom
        r["has_website_candidate"] = bool(r["website"])
        r["legal_form"] = legal_form(r["denomination"])
        conf = r["website_confidence"]
        if et == "missing":
            seg = "A"
        elif et in ("free", "free_typo"):
            seg = "B"
        elif et == "professional_shared":
            seg = "C"
        elif conf in ("high", "medium"):
            seg = "E"
        else:
            seg = "D"
        r["segment"] = SEGMENTS[seg]
        r["segment_code"] = seg
        r["no_pro_email_no_site"] = seg in ("A", "B", "C")
        r["has_phone"] = bool(r["phone"])
        r["contactable"] = "phone+email" if r["phone"] and r["email"] else ("phone" if r["phone"] else ("email" if r["email"] else "none"))

    fields = list(rows[0].keys())
    write("data/arsp_subcontractors_segmented.csv", rows, fields)
    target = [r for r in rows if r["no_pro_email_no_site"]]
    # tri : actives, grosses formes juridiques d'abord, puis secteur
    order = {"SA": 0, "SAS": 0, "SASU": 0, "SARL": 1, "SARLU": 1, "SPRL": 1, "SCS": 1, "SNC": 1, "ETS": 3, "AUTRE": 2}
    target.sort(key=lambda r: (order.get(r["legal_form"], 2), r["sector_primary"], r["province"], r["denomination"]))
    cols = ["id", "denomination", "nom_commercial", "legal_form", "sector_primary", "sectors", "province", "ville", "adresse",
            "phone", "email", "email_type", "segment_code", "rccm", "num_impot", "num_ariane", "date_expiration", "n_records",
            "possible_duplicate_of", "contactable"]
    A = Path("data/analysis")
    write(A / "sans_site_ni_email_pro.csv", target, cols)
    for code in SEGMENTS:
        write(A / f"segment_{code}.csv", [r for r in rows if r["segment_code"] == code], cols)

    def stats(key, name):
        tot, tgt = Counter(r[key] for r in rows), Counter(r[key] for r in target)
        seg = defaultdict(Counter)
        for r in rows:
            seg[r[key]][r["segment_code"]] += 1
        out = [{key: k, "total": tot[k], "sans_site_ni_email_pro": tgt[k], "pct_sans": round(100 * tgt[k] / tot[k], 1),
                **{f"seg_{c}": seg[k][c] for c in SEGMENTS}} for k in tot]
        out.sort(key=lambda x: -x["sans_site_ni_email_pro"])
        write(A / f"stats_{name}.csv", out, list(out[0].keys()))
        return out

    s_sec, s_prov, s_form = stats("sector_primary", "secteur"), stats("province", "province"), stats("legal_form", "forme_juridique")

    n, nt = len(rows), len(target)
    et = Counter(r["email_type"] for r in rows)
    sg = Counter(r["segment_code"] for r in rows)
    md = ["# Analyse de la présence numérique des entreprises ARSP\n",
          f"Base : **{n}** entreprises uniques (registre ARSP, 2026-11-01).\n",
          f"## Résultat principal\n\n**{nt} entreprises ({100*nt/n:.1f} %) n'ont ni e-mail professionnel ni site web détecté** (segments A+B+C).\n",
          "## Répartition par segment\n", "| Segment | Entreprises | % |", "|---|---:|---:|"]
    md += [f"| {SEGMENTS[c]} | {sg[c]} | {100*sg[c]/n:.1f} |" for c in SEGMENTS]
    md += ["\n## Type d'e-mail\n", "| Type | Entreprises | % |", "|---|---:|---:|"]
    md += [f"| {k} | {v} | {100*v/n:.1f} |" for k, v in et.most_common()]

    def table(title, data, label, top=12):
        t = [f"\n## {title}\n", f"| {label} | Total | Sans site ni e-mail pro | % |", "|---|---:|---:|---:|"]
        t += [f"| {d[label]} | {d['total']} | {d['sans_site_ni_email_pro']} | {d['pct_sans']} |" for d in data[:top]]
        return t
    md += table("Par secteur", s_sec, "sector_primary", 25)
    md += table("Par province (top 10)", s_prov, "province", 10)
    md += table("Par forme juridique", s_form, "legal_form", 10)
    c = Counter(r["contactable"] for r in target)
    md += ["\n## Joignabilité de la cible (A+B+C)\n", "| Canal disponible | Entreprises |", "|---|---:|"]
    md += [f"| {k} | {v} |" for k, v in c.most_common()]
    md += ["\n## Réserves\n",
           "- « Sans site » = aucun site déduit de l'e-mail. Une entreprise peut avoir un site non détecté (e-mail Gmail) : à confirmer via la recherche web (pilote proposé).",
           "- Les sites candidats `low`/`medium` ne sont pas vérifiés tant que `verify_websites.py` n'a pas tourné.",
           "- Le segment C regroupe des sociétés dont l'e-mail appartient à un cabinet ; leur propre site est inconnu.",
           f"- {sum(1 for r in target if r['possible_duplicate_of'])} entreprises de la cible ont un doublon possible non fusionné (colonne `possible_duplicate_of`)."]
    (A / "RAPPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:2])
