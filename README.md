# Agentic Job Search

Outil personnel de recherche d'offres en France, de classement par adéquation avec un CV et de préparation des candidatures. L'outil génère des documents ; il n'envoie pas de candidature.

## Exécution

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Placez votre CV PDF à la racine. S'il n'y a qu'un PDF, il est détecté automatiquement : le fichier `Developpeur_Python_Expert_Automatisation.pdf` actuellement présent fonctionne sans argument. Si plusieurs PDF sont présents, choisissez explicitement `--cv` ; l'outil ne devine pas lequel est à jour.

Le texte est extrait avec `pdftotext` lorsqu'il est installé, sinon avec `pypdf`. Les PDF scannés nécessitant un OCR ne sont pas pris en charge. Codex est utilisé si disponible dans le shell ; en cas d'échec, un classement et des documents locaux prennent le relais. `--no-llm` désactive tous les appels au modèle.

```bash
python3 main.py --sample --no-llm
python3 main.py --no-llm --max-per-source 3
python3 main.py --sources france_travail,hellowork
python3 main.py --query "Python LLM" --location "France"
python3 main.py --min-score 4.5
python3 main.py --cv chemin/vers/cv.pdf
python3 main.py --profile chemin/vers/profil.json --cv chemin/vers/cv.pdf
```

Toutes les anciennes options de sortie restent disponibles : `--output`, `--report`, `--tailored-dir` et `--cover-letter-dir`. `--threshold` reste un alias de `--min-score`.

## Positionnement actuel

[search_profile.json](search_profile.json) définit la cible : **Senior Python Engineer | IA Agentique & LLM | Automatisation des Processus Métier**.

- Plusieurs requêtes courtes couvrent le développement Python, le backend, les LLM et l'automatisation.
- Python est requis ; le développement logiciel, l'IA agentique et l'automatisation constituent les priorités.
- SQL, data engineering et DevOps complètent l'adéquation. Les anciennes compétences BI/analytics ne donnent plus de bonus à elles seules.
- Les postes seniors sont privilégiés. Les intitulés juniors, BI/analytics et autres métiers configurés comme éloignés sont plafonnés sous le seuil par défaut de 4/5.
- **Remote, hybride et présentiel sont acceptés**, conformément à votre préférence. Ce réglage prime sur la mobilité inscrite dans le CV pour le classement.

Les compétences comptabilisées localement doivent être présentes à la fois dans l'offre et dans le CV. Les limites liées au métier, aux compétences requises, au niveau et aux descriptions insuffisantes s'appliquent aussi au score du modèle. Les offres retenues sont triées par score décroissant.

Le classement local utilise l'intitulé, les groupes prioritaires, les compétences complémentaires et la séniorité. Il explique les correspondances et les plafonds. Il reste une heuristique : un score de 5 ne garantit pas une adéquation parfaite. Les intitulés atypiques peuvent être sous-évalués ; ajoutez leurs variantes dans `target_roles` si nécessaire. Un seuil inférieur à 4 peut volontairement faire réapparaître des correspondances partielles.

## Changer de profil sans modifier le code

Le **CV contient les faits** ; le **JSON décrit le positionnement recherché**. Remplacer seulement le PDF met à jour les expériences, mais ne change pas automatiquement la cible de carrière. Pour un nouveau positionnement, remplacez le CV et adaptez le JSON, ou sélectionnez un autre fichier avec `--profile`.

| Champ du profil | Rôle |
| --- | --- |
| `headline` | Positionnement à transmettre au classement et à la rédaction |
| `queries` | Requêtes envoyées à chaque source ; `--query` les remplace par une seule |
| `target_roles` | Variantes d'intitulés recherchés, français ou anglais |
| `required_skills` | Compétences devant être attestées dans l'offre et le CV |
| `priority_skills` | Groupes de compétences prioritaires, avec leurs termes |
| `supporting_skills` | Compétences complémentaires, de poids limité |
| `excluded_titles` | Intitulés à déprioriser, même si des compétences correspondent |
| `seniority` | `senior` ou `any` |
| `remote_policy` | `any` : tout accepter ; `prefer` : bonus full remote ; `required` : plafond sous 4 si non confirmé |
| `location` | Zone envoyée aux sources, remplaçable avec `--location` |
| `max_job_age_days` | Ancienneté maximale connue, 14 jours par défaut |
| `min_yearly_salary_eur` | Plancher annuel connu, 40 000 EUR par défaut ; 0 désactive ce seuil |

Ces termes ne créent aucune compétence dans le CV. Il est inutile d'ajouter un outil non maîtrisé uniquement pour augmenter un score. Le mode local conserve le contenu original du CV et met en avant les compétences communes ; il ne réécrit pas les expériences. Le modèle reçoit des consignes de fidélité au CV, mais ses documents restent à relire.

## Sources et limites

Les sept sources restent France Travail, HelloWork, Apec, Indeed, Free-Work, MeteoJob et Welcome to the Jungle. `--sources all` les sélectionne toutes. Le fichier Upwork existe mais n'est pas enregistré dans les sources actives.

`--max-per-source` limite le nombre total d'offres renvoyées par source, toutes requêtes confondues (25 par défaut). Le budget est partagé entre les requêtes, puis les résultats sont entrelacés et dédupliqués. Des doublons, erreurs ou recherches vides peuvent produire moins d'offres que la limite. Plusieurs pages de recherche sont consultées même avec une petite limite.

Les connecteurs lisent du HTML et des données JSON-LD. Une page vide, bloquée ou rendue uniquement en JavaScript peut ne fournir aucune offre. Le pipeline signale les recherches sans résultat exploitable et continue après les erreurs de source. Les modifications sont vérifiées avec des données locales et des connecteurs simulés ; la disponibilité actuelle des sites et les appels Codex réels ne sont pas validés par ces tests.

Une date ou une rémunération absente n'entraîne pas de rejet. Les tarifs journaliers/horaires ne sont pas comparés à un salaire annuel. Le filtre géographique dépend de la recherche des plateformes ; les restrictions précises de pays, de contrat ou d'éligibilité restent à vérifier dans l'annonce. Le classement des modalités de travail est indicatif lorsque le texte est ambigu.

## Résultats

```text
matched_jobs.json
job_search_results.md
tailored_cvs/<entreprise>_<poste>_<identifiant>.md
cover_letters/<entreprise>_<poste>_<identifiant>.md
```

Le JSON contient l'offre, le score, son explication et les chemins des documents. L'identifiant dérivé de l'URL évite d'écraser deux candidatures pour des offres de même intitulé chez la même entreprise.

Exemple avec le nouveau CV et `--sample --no-llm` :

```text
Fetched jobs: 6
Matched jobs (score >= 4.0): 3
Senior Python Engineer - IA Agentique et LLM : 5.0
Développeur Python Senior - Automatisation métier : 5.0
Senior Backend Python Engineer : 4.6
```

Les trois contre-exemples (analytics, junior et RPA sans Python) restent sous le seuil. Les offres sample sont fictives et ne changent pas lorsque vous sélectionnez un autre profil.

## Vérification

```bash
python3 -m unittest discover -s tests -v
python3 main.py --sample --no-llm
python3 -m py_compile main.py job_search/*.py job_search/fetchers/*.py
```

Les tests utilisent des CV synthétiques, des sources simulées et des dossiers temporaires. L'analyse du fonctionnement est détaillée dans [docs/codebase-analysis.md](docs/codebase-analysis.md).
