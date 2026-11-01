"""Déduit les sites web des entreprises à partir du domaine de leur e-mail professionnel.

Méthode (bien plus fiable qu'une recherche Google sur le nom) : une adresse e-mail sur un
domaine propriétaire (contact@societe.cd) pointe presque toujours vers le site officiel.
Garde-fous :
  - exclut les messageries gratuites ET leurs fautes de frappe (gamail.com, gmai.com…)
  - exclut les domaines partagés par plusieurs entreprises distinctes (cabinets, comptables
    qui enregistrent leurs clients) ou appartenant à l'ARSP
  - niveau de confiance :  high   = domaine unique + nom de l'entreprise retrouvé dans le domaine
                           medium= domaine unique, sans correspondance de nom
                           medium= domaine partagé mais un seul propriétaire évident (les autres sociétés sont exclues)
                           low   = domaine partagé par 2-3 entreprises sans propriétaire évident (rejeté si > 3)

Entrée  : data/arsp_subcontractors_dedup.csv
Sorties : data/arsp_websites.csv  (candidats)  +  colonnes website_* ajoutées au dataset final
          data/arsp_subcontractors_enriched.csv / .jsonl
À valider ensuite avec scripts/verify_websites.py (requêtes HTTP réelles).
"""
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict

FREE = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.fr", "yahoo.co.uk", "ymail.com", "hotmail.com", "hotmail.fr",
    "outlook.com", "outlook.fr", "live.com", "live.fr", "msn.com", "icloud.com", "me.com", "aol.com", "mail.com",
    "protonmail.com", "proton.me", "qq.com", "163.com", "126.com", "sina.com", "foxmail.com", "yandex.com",
    "gmx.com", "gmx.fr", "zoho.com", "free.fr", "orange.fr", "wanadoo.fr", "skynet.be", "tutanota.com",
    "arsp.cd", "web.de", "mail.ru", "bk.ru", "inbox.com", "rocketmail.com", "hotmail.co.uk", "live.be", "hotmail.be",
    "yahoo.co.in", "yahoo.ca", "outlook.be", "gmx.net", "mailinator.com", "rediffmail.com",
}
FREE_LABELS = ["gmail", "yahoo", "hotmail", "outlook", "icloud", "live", "protonmail", "ymail"]
STOP = {"sarl", "sarlu", "sas", "sasu", "sa", "ets", "etablissement", "etablissements", "societe", "ste", "entreprise",
        "group", "groupe", "drc", "rdc", "congo", "the", "and", "des", "de", "du", "la", "le", "les", "et", "services",
        "service", "company", "compagnie", "general", "generale", "international", "global", "business"}


def ascii_low(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_free(domain):
    if domain in FREE:
        return True
    label, _, tld = domain.partition(".")
    # fautes de frappe : gamail.com, gmai.com, yaho.fr, hotmai.com…
    return any(lev(label, f) <= 2 and tld in {"com", "fr", "net", "cd", "co", "org"} for f in FREE_LABELS)


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9]{3,}", ascii_low(s)) if t not in STOP]


def acronym(s):
    return "".join(w[0] for w in re.findall(r"[a-z]+", ascii_low(s)) if w not in STOP)


def name_match(domain, *names):
    label = re.sub(r"[^a-z0-9]", "", domain.split(".")[0])
    for nm in names:
        toks = tokens(nm)
        if any(t in label or (len(label) >= 4 and label in t) for t in toks):
            return True
        acr = acronym(nm)
        if len(acr) >= 3 and (label == acr or label.startswith(acr)):
            return True
    return False


def main(src="data/arsp_subcontractors_dedup.csv"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    by_dom = defaultdict(set)
    for r in rows:
        if "@" in r["email"]:
            by_dom[r["email"].split("@")[-1]].add(r["id"])
    match_ids = defaultdict(set)
    for r in rows:
        dom = r["email"].split("@")[-1] if "@" in r["email"] else ""
        if dom and len(by_dom[dom]) > 1 and name_match(dom, r["denomination"], r["nom_commercial"]):
            match_ids[dom].add(r["id"])
    cands = []
    for r in rows:
        dom = r["email"].split("@")[-1] if "@" in r["email"] else ""
        r.update(website="", website_confidence="", website_source="", website_verified="")
        if not dom or is_free(dom) or "." not in dom:
            continue
        n_companies = len(by_dom[dom])
        if n_companies > 3:
            continue
        match = name_match(dom, r["denomination"], r["nom_commercial"])
        if n_companies > 1:
            # Domaine partagé : seul le propriétaire probable (celui dont le nom est dans le domaine)
            # reçoit le site, à condition qu'il soit le seul à correspondre.
            owners = [x for x in by_dom[dom] if x in match_ids.get(dom, set())]
            if len(owners) == 1:
                if r["id"] != owners[0]:
                    continue
                conf = "medium"
            else:
                conf = "low"
        else:
            conf = "high" if match else "medium"
        r.update(website=f"https://{dom}", website_confidence=conf, website_source="email_domain")
        cands.append({"id": r["id"], "denomination": r["denomination"], "nom_commercial": r["nom_commercial"],
                      "domain": dom, "confidence": conf, "name_in_domain": match, "n_companies_on_domain": n_companies})
    with open("data/arsp_websites.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(cands[0].keys()))
        w.writeheader(); w.writerows(cands)
    fields = list(rows[0].keys())
    with open("data/arsp_subcontractors_enriched.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    with open("data/arsp_subcontractors_enriched.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: (r[k] == "True" if k == "is_expired" else r[k]) for k in fields}, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(rows), "entreprises;", len(cands), "sites candidats;", Counter(c["confidence"] for c in cands))


if __name__ == "__main__":
    main(*sys.argv[1:2])
