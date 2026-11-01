"""Collecte POLIE du flux public « Annonces légales » du RCCM National (https://rccm.cd/annonces).

Ce flux est celui que la page ouverte charge elle-même, sans authentification
(GET /rest/entities/annonces?skip=K&limit=40). Ce script :
  - fait UNE requête à la fois, avec un délai fixe (par défaut 2 s) ;
  - s'identifie honnêtement (User-Agent + contact) ;
  - reprend là où il s'est arrêté (data/rccm/state.json) ;
  - S'ARRÊTE immédiatement si le portail réclame une authentification, un captcha, ou limite le débit.
    Il ne tente JAMAIS de contourner une protection (pas de rotation d'IP, pas de captcha, pas de compte).
  - ne conserve pas les jetons `access` (liés au téléchargement des statuts, hors périmètre).

Usage : python scripts/rccm_collect.py --contact vous@exemple.cd [--delay 2] [--max-pages 50]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://rccm.cd/rest/entities/annonces"
OUT = Path("data/rccm")
FEED = OUT / "annonces.jsonl"
STATE = OUT / "state.json"
LIMIT = 40


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"skip": 0, "done": False}


def seen_ids():
    ids = set()
    if FEED.exists():
        for line in FEED.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ids.add(json.loads(line)["_id"])
    return ids


def stop(reason):
    print(f"\nARRÊT : {reason}\nLe portail protège cet accès : ne pas insister. "
          "Contactez le GUCE (guce@guichetunique.cd) pour un accès officiel.", file=sys.stderr)
    sys.exit(2)


def fetch(session, skip):
    for attempt in (1, 2):
        r = session.get(BASE, params={"skip": skip, "limit": LIMIT}, timeout=30)
        if r.status_code == 429 and attempt == 1:
            wait = min(int(r.headers.get("Retry-After", "60") or 60), 300)
            print(f"429 reçu, pause de {wait}s (une seule nouvelle tentative)…")
            time.sleep(wait)
            continue
        if r.status_code in (401, 403, 429):
            stop(f"HTTP {r.status_code} (accès refusé / débit limité) à skip={skip}")
        r.raise_for_status()
        if "json" not in r.headers.get("Content-Type", ""):
            stop(f"réponse non JSON à skip={skip} (page de vérification anti-robot ?)")
        data = r.json()
        if "captcha" in json.dumps(data)[:500].lower():
            stop("le portail demande une vérification anti-robot")
        return data
    stop("échec répété")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contact", required=True, help="e-mail de contact inclus dans le User-Agent")
    ap.add_argument("--delay", type=float, default=2.0, help="secondes entre deux requêtes (min 1.0)")
    ap.add_argument("--max-pages", type=int, default=0, help="0 = jusqu'à la fin")
    a = ap.parse_args()
    delay = max(a.delay, 1.0)
    OUT.mkdir(parents=True, exist_ok=True)

    s = requests.Session()
    s.headers.update({"Accept": "application/json",
                      "User-Agent": f"arsp-dataset-drc/1.0 (research; contact: {a.contact})"})
    state, known, pages, added = load_state(), seen_ids(), 0, 0
    if state.get("done"):
        print("Déjà terminé. Supprimez data/rccm/state.json pour recommencer.")
        return
    with open(FEED, "a", encoding="utf-8") as out:
        while True:
            data = fetch(s, state["skip"])
            for item in data.get("annonces", []):
                item.pop("access", None)
                if item["_id"] not in known:
                    known.add(item["_id"])
                    out.write(json.dumps(item, ensure_ascii=False) + "\n")
                    added += 1
            out.flush()
            pages += 1
            state["skip"] = data.get("nextSkip", state["skip"] + LIMIT)
            state["done"] = not data.get("hasMore", False)
            STATE.write_text(json.dumps(state))
            print(f"skip={state['skip']:>7}  +{len(data.get('annonces', []))}  total={len(known)}", flush=True)
            if state["done"] or (a.max_pages and pages >= a.max_pages):
                break
            time.sleep(delay)
    print(f"Terminé pour cette session : {added} nouvelles annonces, {len(known)} au total.")


if __name__ == "__main__":
    main()
