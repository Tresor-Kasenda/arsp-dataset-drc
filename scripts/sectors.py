"""Normalise les secteurs d'activité ARSP en catégories.

Entrée  : data/arsp_subcontractors.csv
Sortie  : data/arsp_subcontractors_sectors.csv  (+ colonnes sector_*)
          data/sector_mapping.csv               (libellé brut -> catégories, pour audit)

Colonnes ajoutées :
  sector_primary   catégorie principale
  sectors          toutes les catégories détectées, séparées par « ; »
  sector_source    activite | denomination (déduit du nom) | none
"""
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# (catégorie, regex sur texte en MAJUSCULES sans accents). L'ordre = priorité à égalité de position.
RULES = [
    ("Construction & BTP", r"CONSTRU(?!CTION MECANIQ)|CONSTUC|CONTRUCTION|GENIE ?CIVIL|GENEI|BATIMENT|\bBTP\b|TRAVAUX PU|PUPLIC|ARCHITECT|TERRASSEMENT|BETON|MACONN|PLOMBERIE|MENUISERIE|PEINTURE"),
    ("Mines & forage", r"MINIER|MINIERE|MIMNIERE|EXTRACTION|MINING|MINES?\b|EXPLOITATION MIN|EXPOITATION MIN|FORAGE|DRILLING|CARRIERE|GEOLOG|OR ET DIAMANT"),
    ("Énergie & hydrocarbures", r"HYDROCARBUR|HYDRCARBUR|RAFFIN|PETROL|CARBURANT|ELECTRI|ENERG|SOLAIRE|GROUPE ELECTROGENE|GAZ\b|LUBRIFIANT"),
    ("Eau & assainissement", r"ASSAINISS|\bEAU\b|D'EAU|HYGIENE|DECHETS|DERATISATION|DESINSECT|FUMIGATION"),
    ("Transport & logistique", r"TRANSPORT|TANSPORT|LOGISTIC|LOGISTIQ|AERONAUT|DOUANE|TRANSITAIRE|STOCKAGE|CARGO|FRET|MANUTENTION|COURRIER|AERIEN|LOCATION DES? (VEHICULE|ENGIN)"),
    ("Informatique & télécoms", r"INFORMATIQ|ELECTRONOQUE|TELECOM|NUMERIQUE|DIGITAL|LOGICIEL|RESEAU|ELECTRONIQ|ELECTRO-TECH|AUTOMATION|TECHNOLOGIE|\bIT\b|INTERNET"),
    ("Communication & médias", r"(?<!TELE)COMMUNICATION|PUBLICITE|MEDIA|IMPRIMERIE|EVENEMENT|MARKETING|AUDIOVISUEL|PHOTO"),
    ("Conseil & services professionnels", r"CONSEIL|CONSULT|AUDIT|ETUDES?\b|INGENIERIE|JURIDIQUE|AVOCAT|COMPTAB|EXPERTISE|RECHERCHE|CERTIFICATION|NORMALISATION|TOPOGRAPH"),
    ("Ressources humaines", r"PLACEMENT (DU )?PERSONNEL|RESSOURCES HUMAINES|INTERIM|RECRUTEMENT|MAIN D'?OEUVRE|SOUS-?TRAITANCE DE MAIN"),
    ("Sécurité & gardiennage", r"SECURITE|GARDINAGE|GARDIENNAGE|SURVEILLANCE|SECURITY"),
    ("Santé & pharmacie", r"SANTE|MEDECINE|MEDICA|PHARMA|CLINIQUE|HOPITAL|LABORATOIRE|OPTIQUE"),
    ("Agriculture & agroalimentaire", r"AGRI|AGRO|FORESTIER|ELEVAGE|PECHE|ALIMENTAIRE|BOULANGERIE|SEMENCE|PLANTATION|AQUACULTURE"),
    ("Hôtellerie, restauration & tourisme", r"HOTEL|RESTAUR|CATERING|\bCAFE\b|TOURISM|TRAITEUR|VOYAGE"),
    ("Maintenance, entretien & réparation", r"NETTOYAGE|ENTRETIEN|MAINTENANCE|REPARATION|JARDINAGE|BLANCHISSERIE"),
    ("Éducation & formation", r"EDUCATION|FORMATION|ENSEIGNEMENT|ECOLE|UNIVERSIT"),
    ("Industrie & manufacture", r"INDUSTRI|MANUFACT|TEXTILE|CHIMI|MECANIQ|METALL|SIDERURG|USINAGE|FABRICATION|AUTOMOBILE|ARTISANAT|EMBALLAGE|PLASTIQ"),
    ("Immobilier", r"IMMOBILI|PROMOTION IMMO"),
    ("Finance & assurance", r"FINANC|ASSURANCE|BANQUE|MICROFINANCE|CREDIT\b|TRANSFERT D'ARGENT"),
    ("Commerce & fournitures", r"COMMERC|FOURNITURE|FOURNIT|IMPORT|EXPORT|VENTE|QUINCAILLERIE|DISTRIBUTION|ACHAT|NEGOCE|\bBIENS\b|\bPRODUITS\b|MATERIEL"),
    ("Services généraux", r"SERVICE|SEVICES|SRVICES|PRESTATION|MULTI-?SERV|DIVERS|AUTRES"),
]
GENERIC = {"Services généraux", "Commerce & fournitures"}
COMPILED = [(c, re.compile(p)) for c, p in RULES]
NONE = "Non précisé"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", s).strip()


def classify(text: str):
    """-> liste ordonnée de catégories (spécifiques d'abord, génériques en dernier)."""
    t = norm(text)
    hits = []
    for cat, rx in COMPILED:
        m = rx.search(t)
        if m:
            hits.append((cat in GENERIC, m.start(), cat))
    hits.sort()
    return [h[2] for h in hits]


def main(src="data/arsp_subcontractors.csv", dst="data/arsp_subcontractors_sectors.csv"):
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    mapping = Counter()
    for r in rows:
        cats, source = classify(r["activite"]), "activite"
        if not cats:
            # Repli sur le nom : uniquement les catégories spécifiques (jamais « Services généraux »)
            cats = [c for c in classify(f"{r['denomination']} {r['nom_commercial']}") if c not in GENERIC]
            source = "denomination" if cats else "none"
        r["sector_primary"] = cats[0] if cats else NONE
        r["sectors"] = ";".join(cats) if cats else NONE
        r["sector_source"] = source
        if source == "activite":
            mapping[(r["activite"], r["sector_primary"], r["sectors"])] += 1
    fields = list(rows[0].keys())
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(Path(dst).parent / "sector_mapping.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["activite_brute", "sector_primary", "sectors", "n"])
        for (a, p, s), n in sorted(mapping.items(), key=lambda x: -x[1]):
            w.writerow([a, p, s, n])
    print(Counter(r["sector_primary"] for r in rows).most_common())
    print(Counter(r["sector_source"] for r in rows))


if __name__ == "__main__":
    main(*sys.argv[1:3])
