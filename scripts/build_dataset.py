"""Nettoie l'export brut ARSP et produit les datasets (CSV + JSONL).

Usage : python scripts/build_dataset.py data/raw/arsp_companies_export_AAAA-MM-JJ.json
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

COLUMNS = [
    "id", "num_dossier", "num_ariane", "num_serie", "denomination", "nom_commercial",
    "rccm", "num_impot", "activite", "adresse", "ville", "province", "province_raw",
    "phone", "email", "created_at", "date_expiration", "is_expired",
]


def clean_text(v):
    if v is None:
        return ""
    v = unicodedata.normalize("NFC", str(v))
    return re.sub(r"\s+", " ", v).strip()


PROVINCES = {
    "haut-katanga": "Haut-Katanga", "katanga": "Haut-Katanga", "lualaba": "Lualaba",
    "kinshasa": "Kinshasa", "kongo-central": "Kongo-Central", "kongo-cenral": "Kongo-Central",
    "haut-uele": "Haut-Uele", "bas-uele": "Bas-Uele", "nord-kivu": "Nord-Kivu",
    "sud-kivu": "Sud-Kivu", "tshopo": "Tshopo", "ituri": "Ituri", "tanganyika": "Tanganyika",
    "maniema": "Maniema", "equateur": "Équateur", "kwilu": "Kwilu", "kasai": "Kasaï",
    "kasai oriental": "Kasaï-Oriental", "kasai-oriental": "Kasaï-Oriental",
    "kasai central": "Kasaï-Central", "kasai-central": "Kasaï-Central",
    "sud-ubangi": "Sud-Ubangi", "nord-ubangi": "Nord-Ubangi", "mongala": "Mongala",
    "haut-lomami": "Haut-Lomami", "lomami": "Lomami", "kwango": "Kwango",
    "mai-ndombe": "Mai-Ndombe", "sankuru": "Sankuru", "tshuapa": "Tshuapa",
}


def clean_province(v):
    v = clean_text(v)
    key = unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode().lower()
    key = re.sub(r"\s*-\s*", "-", key)
    key = re.sub(r"^province (du |de |de la )?", "", key)
    key = {"tanganika": "tanganyika"}.get(key, key)
    return PROVINCES.get(key, PROVINCES.get(key.replace(" ", "-"), PROVINCES.get(key.replace("-", " "), v)))


def clean_phone(v):
    v = re.sub(r"[^\d+]", "", clean_text(v))
    if v.startswith("00243"):
        v = "+" + v[2:]
    elif re.fullmatch(r"0\d{9}", v):
        v = "+243" + v[1:]
    elif re.fullmatch(r"243\d{9}", v):
        v = "+" + v
    return v


def clean_email(v):
    v = clean_text(v).lower().replace(" ", "")
    return v if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) else ""


def clean_date(v):
    v = clean_text(v)
    return v[:10] if re.match(r"\d{4}-\d{2}-\d{2}", v) else ""


def build(src: Path, today: str):
    rows = json.loads(src.read_text(encoding="utf-8"))["data"]
    out = []
    for r in rows:
        rec = {
            "id": r["id"],
            "num_dossier": r["num_dossier"],
            "num_ariane": r["num_ariane"],
            "num_serie": clean_text(r["num_serie"]).replace(",", "."),
            "denomination": clean_text(r["denomination"]),
            "nom_commercial": clean_text(r["nom_commercial"]),
            "rccm": clean_text(r["rccm"]).upper(),
            "num_impot": clean_text(r["num_impot"]).upper(),
            "activite": clean_text(r["activite"]).upper(),
            "adresse": clean_text(r["adresse"]),
            "ville": clean_text(r["ville"]).upper(),
            "province_raw": clean_text(r["province"]),
            "province": clean_province(r["province"]),
            "phone": clean_phone(r["phone"]),
            "email": clean_email(r["email"]),
            "created_at": clean_text(r["created_at"]),
            "date_expiration": clean_date(r["date_expiration"]),
        }
        rec["is_expired"] = bool(rec["date_expiration"] and rec["date_expiration"] < today)
        out.append(rec)
    out.sort(key=lambda x: x["id"])
    return out


def main(src, out_dir="data"):
    from datetime import date
    out = build(Path(src), date.today().isoformat())
    d = Path(out_dir)
    d.mkdir(exist_ok=True)
    with open(d / "arsp_subcontractors.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)
    with open(d / "arsp_subcontractors.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out)} entreprises -> {d}/arsp_subcontractors.{{csv,jsonl}}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
