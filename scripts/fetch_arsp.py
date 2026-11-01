"""Télécharge le registre complet des entreprises ARSP.

Utilise le même endpoint public que le bouton « Export list » de
https://arsp.cd/en/list-of-registered-companies (GET /api/companies/export).

Usage : python scripts/fetch_arsp.py [dossier_sortie]
"""
import json
import sys
from datetime import date
from pathlib import Path

import requests

BASE = "https://arsp.cd/api/companies"
HEADERS = {"Accept": "application/json", "User-Agent": "arsp-dataset-drc/1.0"}


def main(out_dir: str = "data/raw") -> Path:
    count = requests.get(f"{BASE}/count", headers=HEADERS, timeout=30).json()["data"]["count"]
    resp = requests.get(f"{BASE}/export", headers=HEADERS, timeout=180)
    resp.raise_for_status()
    payload = resp.json()
    if len(payload["data"]) != count:
        raise SystemExit(f"Incohérence : export={len(payload['data'])} / count={count}")
    out = Path(out_dir) / f"arsp_companies_export_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"{len(payload['data'])} entreprises -> {out}")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:2])
