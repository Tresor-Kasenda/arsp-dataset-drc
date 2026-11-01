# arsp-dataset-drc

Dataset des entreprises sous-traitantes enregistrées auprès de l'**ARSP**
(Autorité de Régulation de la Sous-traitance dans le Secteur Privé, RDC).

Source : <https://arsp.cd/en/list-of-registered-companies> — **8 780 entreprises** au 2026-11-01.

## Fichiers

| Fichier | Contenu |
|---|---|
| `data/raw/arsp_companies_export_AAAA-MM-JJ.json` | Réponse brute de l'API (non modifiée), 8 780 lignes |
| `data/arsp_subcontractors.csv` / `.jsonl` | Étape 1 : nettoyé (provinces, téléphones, textes) |
| `data/arsp_subcontractors_sectors.csv` | Étape 2 : + secteurs normalisés |
| `data/arsp_subcontractors_dedup.csv` | Étape 3 : **8 727 entreprises uniques** |
| **`data/arsp_subcontractors_enriched.csv` / `.jsonl`** | **Dataset final** : dédupliqué + secteurs + sites web |
| `data/sector_mapping.csv` | Audit : libellé brut -> catégories |
| `data/duplicate_clusters.csv` | Audit : les 53 doublons fusionnés et la règle utilisée |
| `data/arsp_websites.csv` | Sites candidats avec niveau de confiance |

## Pipeline

```bash
pip install requests beautifulsoup4
python scripts/fetch_arsp.py                                   # 1. export brut
python scripts/build_dataset.py data/raw/arsp_companies_export_<date>.json   # 2. nettoyage
python scripts/sectors.py                                      # 3. secteurs
python scripts/dedupe.py                                       # 4. déduplication
python scripts/websites.py                                     # 5. sites candidats + dataset final
python scripts/verify_websites.py                              # 6. vérification HTTP (accès Internet requis)
```

## Schéma du dataset final

Identité : `id`, `num_dossier`, `num_ariane` (n° ARSP), `num_serie`, `denomination`, `nom_commercial`, `rccm`, `num_impot`.
Localisation : `adresse`, `ville`, `province` (normalisée), `province_raw`. Contact : `phone` (+243…), `email`.
Dates : `created_at`, `date_expiration`, `is_expired`, `first_registered`, `last_registered`.

**Secteurs** : `activite` (brut), `sector_primary` (21 catégories), `sectors` (toutes, séparées par `;`),
`sector_source` = `activite` | `denomination` (déduit du nom, moins fiable) | `none`.

**Déduplication** : `n_records`, `all_ids` (tous les `id` fusionnés), `possible_duplicate_of`.
On ne fusionne que sur preuves croisées (même RCCM + même n° d'impôt, ou RCCM/impôt + nom similaire).
Un identifiant partagé avec un nom différent est presque toujours une erreur de saisie : l'entreprise est
conservée et signalée dans `possible_duplicate_of`. L'enregistrement le plus récent est gardé.

**Sites web** : `website`, `website_confidence`, `website_source`, `website_verified`.
Méthode : domaine de l'e-mail professionnel (hors messageries gratuites, fautes de frappe comprises, et hors
domaines partagés par >3 sociétés). `high` = domaine unique contenant le nom ; `medium` = unique sans
correspondance de nom, ou partagé avec un propriétaire évident ; `low` = partagé sans propriétaire clair.
`website_verified` reste vide tant que `verify_websites.py` n'a pas été exécuté.
Un test réel sur 3 domaines a confirmé la nécessité de la vérification : un `medium` n'existe plus (DNS),
un `high` a un certificat TLS invalide mais existe, et un domaine partagé appartenait bien à une seule société.

Le site charge son tableau via `GET /api/companies/export` (aussi `/api/companies/count` et
`/api/companies?page=&per_page=&search=`). Le scraper HTML d'origine (`index.py`) ne fonctionne plus
depuis la refonte Next.js du site.

## Limites connues

- ~700 entreprises n'ont pas de secteur (`Non précisé`) ; ~265 secteurs sont déduits du nom.
- ~225 entreprises ont un identifiant partagé avec une autre (signalé, non fusionné).
- Seules ~14 % des entreprises ont un e-mail professionnel : la plupart utilisent Gmail, donc sans site déductible.
- Contient des coordonnées (téléphone, e-mail), parfois personnelles : à utiliser dans le respect de la vie privée.
- Les anciens fichiers à la racine (`output.txt`, `sorted.txt`, `*domains*.txt`) datent de la v1 (~5 780 entreprises) et sont conservés pour référence.
