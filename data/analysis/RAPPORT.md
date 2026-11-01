# Analyse de la présence numérique des entreprises ARSP

Base : **8727** entreprises uniques (registre ARSP, 2026-11-01).

## Résultat principal

**7452 entreprises (85.4 %) n'ont ni e-mail professionnel ni site web détecté** (segments A+B+C).

## Répartition par segment

| Segment | Entreprises | % |
|---|---:|---:|
| A - Aucun e-mail | 18 | 0.2 |
| B - E-mail gratuit uniquement, sans site | 7384 | 84.6 |
| C - E-mail sur domaine partagé (cabinet/agence), sans site propre | 50 | 0.6 |
| D - E-mail pro / site candidat peu fiable (low) | 89 | 1.0 |
| E - E-mail pro + site candidat (high/medium) | 1186 | 13.6 |

## Type d'e-mail

| Type | Entreprises | % |
|---|---:|---:|
| free | 7349 | 84.2 |
| professional | 1275 | 14.6 |
| professional_shared | 50 | 0.6 |
| free_typo | 35 | 0.4 |
| missing | 18 | 0.2 |

## Par secteur

| sector_primary | Total | Sans site ni e-mail pro | % |
|---|---:|---:|---:|
| Services généraux | 2785 | 2410 | 86.5 |
| Commerce & fournitures | 1750 | 1485 | 84.9 |
| Construction & BTP | 1571 | 1427 | 90.8 |
| Non précisé | 700 | 613 | 87.6 |
| Transport & logistique | 488 | 404 | 82.8 |
| Mines & forage | 220 | 177 | 80.5 |
| Énergie & hydrocarbures | 220 | 159 | 72.3 |
| Informatique & télécoms | 224 | 131 | 58.5 |
| Conseil & services professionnels | 156 | 118 | 75.6 |
| Agriculture & agroalimentaire | 129 | 114 | 88.4 |
| Sécurité & gardiennage | 103 | 91 | 88.3 |
| Maintenance, entretien & réparation | 89 | 79 | 88.8 |
| Hôtellerie, restauration & tourisme | 68 | 59 | 86.8 |
| Industrie & manufacture | 59 | 48 | 81.4 |
| Santé & pharmacie | 52 | 45 | 86.5 |
| Communication & médias | 43 | 33 | 76.7 |
| Éducation & formation | 25 | 18 | 72.0 |
| Eau & assainissement | 16 | 16 | 100.0 |
| Ressources humaines | 14 | 14 | 100.0 |
| Immobilier | 7 | 6 | 85.7 |
| Finance & assurance | 8 | 5 | 62.5 |

## Par province (top 10)

| province | Total | Sans site ni e-mail pro | % |
|---|---:|---:|---:|
| Haut-Katanga | 3987 | 3405 | 85.4 |
| Kinshasa | 2918 | 2379 | 81.5 |
| Lualaba | 963 | 856 | 88.9 |
| Haut-Uele | 214 | 210 | 98.1 |
| Nord-Kivu | 145 | 125 | 86.2 |
| Kongo-Central | 113 | 107 | 94.7 |
| Tshopo | 101 | 97 | 96.0 |
| Kasaï-Oriental | 83 | 83 | 100.0 |
| Sud-Kivu | 90 | 83 | 92.2 |
| Ituri | 52 | 48 | 92.3 |

## Par forme juridique

| legal_form | Total | Sans site ni e-mail pro | % |
|---|---:|---:|---:|
| SARL | 5695 | 4861 | 85.4 |
| SARLU | 1521 | 1293 | 85.0 |
| ETS | 933 | 873 | 93.6 |
| SAS | 264 | 182 | 68.9 |
| AUTRE | 196 | 172 | 87.8 |
| SASU | 76 | 47 | 61.8 |
| SA | 42 | 24 | 57.1 |

## Joignabilité de la cible (A+B+C)

| Canal disponible | Entreprises |
|---|---:|
| phone+email | 7421 |
| phone | 16 |
| email | 13 |
| none | 2 |

## Réserves

- « Sans site » = aucun site déduit de l'e-mail. Une entreprise peut avoir un site non détecté (e-mail Gmail) : à confirmer via la recherche web (pilote proposé).
- Les sites candidats `low`/`medium` ne sont pas vérifiés tant que `verify_websites.py` n'a pas tourné.
- Le segment C regroupe des sociétés dont l'e-mail appartient à un cabinet ; leur propre site est inconnu.
- 195 entreprises de la cible ont un doublon possible non fusionné (colonne `possible_duplicate_of`).
