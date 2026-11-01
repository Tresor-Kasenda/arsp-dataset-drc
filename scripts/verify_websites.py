"""Vérifie les sites candidats par de vraies requêtes HTTP (à lancer sur une machine avec accès Internet).

Pour chaque domaine de data/arsp_websites.csv :
  1. le site répond-il (HTTPS puis HTTP, redirections suivies) ?
  2. le nom de l'entreprise (ou son sigle) apparaît-il dans le <title>, la balise og:site_name ou le corps ?
Résultat -> data/arsp_websites_verified.csv avec  status = verified | live_unconfirmed | dead
  verified         : site actif ET nom retrouvé dans la page
  live_unconfirmed : site actif mais nom non retrouvé (domaine générique, page parking, agence…)
  dead             : pas de réponse / DNS inexistant

Usage : pip install requests beautifulsoup4
        python scripts/verify_websites.py [--workers 20] [--limit N]
"""
import argparse
import csv
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (arsp-dataset-drc verification bot)"}
STOP = {"sarl", "sarlu", "sas", "sasu", "sa", "ets", "etablissement", "etablissements", "societe", "ste", "entreprise",
        "group", "groupe", "drc", "rdc", "congo", "the", "and", "des", "de", "du", "la", "le", "les", "et", "services"}
PARKING = re.compile(r"domain (is )?for sale|buy this domain|parked|coming soon|account suspended|godaddy|hostinger|"
                     r"default web page|apache2 ubuntu|welcome to nginx|index of /", re.I)


def ascii_low(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def name_tokens(*names):
    out = set()
    for n in names:
        out |= {t for t in re.findall(r"[a-z0-9]{3,}", ascii_low(n)) if t not in STOP}
    return out


def fetch(domain):
    for scheme in ("https", "http"):
        for verify in (True, False):  # certificat cassé != site inexistant
            try:
                r = requests.get(f"{scheme}://{domain}", headers=HEADERS, timeout=12, allow_redirects=True, verify=verify)
                r.tls_ok = verify
                if r.status_code < 400:
                    return r
                break
            except requests.exceptions.SSLError:
                continue
            except requests.RequestException:
                break
    return None


def check(row):
    r = fetch(row["domain"])
    out = dict(row, status="dead", final_url="", title="", matched_tokens="", tls_ok="")
    if r is None:
        return out
    soup = BeautifulSoup(r.text[:300_000], "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    og = soup.find("meta", property="og:site_name")
    hay = ascii_low(" ".join([title, og["content"] if og and og.get("content") else "", soup.get_text(" ")[:20_000]]))
    toks = name_tokens(row["denomination"], row["nom_commercial"])
    hit = sorted(t for t in toks if t in hay)
    out.update(tls_ok=r.tls_ok, final_url=r.url, title=title[:120], matched_tokens=",".join(hit))
    out["status"] = "verified" if hit and not PARKING.search(hay[:3000]) else "live_unconfirmed"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    rows = list(csv.DictReader(open("data/arsp_websites.csv", encoding="utf-8-sig")))
    if a.limit:
        rows = rows[: a.limit]
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(check, rows))
    with open("data/arsp_websites_verified.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader(); w.writerows(res)
    from collections import Counter
    print(Counter(r["status"] for r in res))


if __name__ == "__main__":
    main()
