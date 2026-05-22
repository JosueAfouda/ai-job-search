# Prompt Template d'Adaptation

Ce prompt permet a un utilisateur d'adapter la solution a son profil, son marche et ses sources d'offres sans modifier l'architecture globale du projet.

```text
Tu travailles dans le codebase actuel d'une solution Python CLI de recherche d'emploi et de tailoring de CV.

## Objectif

Adapte cette solution a mon contexte personnel de recherche d'emploi, sans changer son architecture generale.

La solution doit conserver :
- `main.py` comme point d'entree CLI ;
- `job_search/pipeline.py` comme orchestrateur ;
- les modeles partages dans `job_search/models.py` ;
- les fetchers de job boards dans `job_search/fetchers/` ;
- les composants existants de scoring, CV tailoring, cover letter generation et LLM wrapper ;
- les modes locaux et deterministes, notamment `--sample` et `--no-llm`.

Tu dois adapter le codebase a mon profil et a mon marche cible, pas le reecrire.

## Mon contexte

### Profil candidat
- Pays de residence : {{PAYS_RESIDENCE}}
- Pays ou zones ciblees : {{PAYS_OU_ZONES_CIBLEES}}
- Metier principal recherche : {{METIER_CIBLE}}
- Metiers proches acceptables : {{METIERS_ALTERNATIFS}}
- Niveau d'experience : {{NIVEAU_EXPERIENCE}}
- Langues de travail : {{LANGUES}}
- Types de contrat recherches : {{TYPES_CONTRAT}}
- Modes de travail acceptes : {{REMOTE_HYBRIDE_PRESENTIEL}}
- Contraintes importantes : {{CONTRAINTES_IMPORTANTES}}

### Profil technique et metier
- Competences fortes : {{COMPETENCES_FORTES}}
- Competences secondaires : {{COMPETENCES_SECONDAIRES}}
- Outils principaux : {{OUTILS_PRINCIPAUX}}
- Domaines metier connus : {{DOMAINES_METIER}}
- Certifications ou diplomes importants : {{CERTIFICATIONS_DIPLOMES}}
- Elements a valoriser dans le CV : {{ELEMENTS_A_VALORISER}}
- Elements a eviter ou de-prioriser : {{ELEMENTS_A_EVITER}}

### Recherche d'emploi
- Requete de recherche par defaut souhaitee : {{REQUETE_DE_RECHERCHE}}
- Localisation de recherche par defaut : {{LOCALISATION_RECHERCHE}}
- Seuil minimum de matching souhaite : {{SEUIL_SCORE}}
- Nombre maximal d'offres par source par defaut : {{MAX_OFFRES_PAR_SOURCE}}

### Job boards et sources
Adapte les sources d'offres au marche cible.

Sources a privilegier si elles sont pertinentes :
{{JOB_BOARDS_PRIORITAIRES}}

Sources a retirer ou desactiver si elles ne sont pas pertinentes :
{{JOB_BOARDS_A_RETIRER}}

Si certaines sources specifiques au pays ou au metier sont necessaires mais absentes :
1. identifie les job boards pertinents ;
2. ajoute les fetchers necessaires dans `job_search/fetchers/` en suivant les patterns existants ;
3. conserve une gestion robuste des erreurs si un site bloque, change son HTML ou ne repond pas ;
4. normalise toujours les offres vers le modele partage `Job`.

## Adaptations attendues

### 1. Configuration de recherche
- Mets a jour les valeurs par defaut pertinentes dans la CLI et le pipeline :
  - requete par defaut ;
  - localisation par defaut ;
  - sources par defaut ;
  - parametres raisonnables pour mon marche.
- Garde les options CLI existantes compatibles autant que possible.

### 2. Sources d'offres
- Examine les fetchers existants.
- Conserve ceux qui restent utiles a mon contexte.
- Desactive ou retire des sources par defaut celles qui ne sont pas adaptees.
- Ajoute uniquement les fetchers necessaires pour mes job boards cibles.
- Ne melange pas le parsing specifique aux sources avec la logique centrale du pipeline.

### 3. Scoring adapte a mon profil
Adapte la logique de scoring pour mieux classer les offres selon mon profil.

Le scoring doit prendre en compte au minimum :
- adequation avec le metier cible ;
- competences cles ;
- niveau d'experience demande ;
- localisation et mode de travail ;
- langue ou contraintes geographiques si pertinentes ;
- type de contrat si disponible ;
- signaux negatifs : poste trop eloigne du profil, exigences incompatibles, localisation impossible, stack non pertinente.

Si le scoring LLM est utilise :
- adapte les prompts de scoring a mon profil ;
- garde un fallback local utilisable avec `--no-llm`.

Si un scoring heuristique local existe :
- adapte les mots-cles, ponderations ou regles pour mon metier ;
- evite de survaloriser des competences non centrales.

### 4. CV et lettres de motivation
- Adapte les instructions de tailoring afin que les CV et lettres generes mettent en avant les experiences et competences pertinentes pour mon profil.
- Ne fabrique pas d'experience ou de competence absente du CV source.
- Garde les sorties generees dans les dossiers prevus par l'architecture existante.

### 5. Samples et verification
- Mets a jour ou ajoute des offres sample adaptees a mon contexte afin que `--sample --no-llm` reste utile.
- Verifie que les changements fonctionnent localement.
- Execute au minimum :
  - `python3 main.py --sample --no-llm`
  - `python3 -m py_compile main.py job_search/*.py job_search/fetchers/*.py`
- Si des tests existent ou si tu ajoutes une logique risquee, ajoute des tests cibles.

## Contraintes de conception

- Ne change pas l'architecture globale du projet.
- Ne transforme pas le CLI en application web.
- Ne mets pas les informations personnelles en dur partout dans le code : centralise les adaptations dans les endroits coherents avec l'architecture existante.
- Ne casse pas les options existantes sans raison solide.
- Ne rends pas la solution dependante de services externes pour les modes `--sample` et `--no-llm`.
- Garde le code lisible, type et conforme aux conventions deja presentes dans le depot.

## Methode de travail attendue

1. Inspecte d'abord le codebase et explique brievement ou les adaptations seront faites.
2. Implemente les changements necessaires.
3. Verifie les changements avec les commandes locales pertinentes.
4. Resume :
   - les fichiers modifies ;
   - les nouvelles sources d'offres ajoutees ou les sources par defaut modifiees ;
   - les changements de scoring ;
   - les hypotheses prises ;
   - les limites restantes, notamment sur les job boards live.
```

## Exemple : Data Analyst base au Senegal

```text
{{PAYS_RESIDENCE}} = Senegal
{{PAYS_OU_ZONES_CIBLEES}} = Senegal, Afrique francophone, Remote international
{{METIER_CIBLE}} = Data Analyst
{{METIERS_ALTERNATIFS}} = Business Intelligence Analyst, Reporting Analyst, BI Developer junior/intermediaire
{{NIVEAU_EXPERIENCE}} = Intermediaire
{{LANGUES}} = Francais, Anglais
{{TYPES_CONTRAT}} = CDI, CDD, missions freelance pertinentes
{{REMOTE_HYBRIDE_PRESENTIEL}} = Remote, hybride, presentiel au Senegal
{{CONTRAINTES_IMPORTANTES}} = Prioriser les offres accessibles depuis le Senegal et eviter les postes exigeant une presence permanente hors zone cible

{{COMPETENCES_FORTES}} = SQL, Power BI, Excel avance, Python pour l'analyse, data visualization, reporting, KPI
{{COMPETENCES_SECONDAIRES}} = Tableau, ETL leger, statistiques descriptives, data quality
{{OUTILS_PRINCIPAUX}} = SQL, Power BI, Python, Excel
{{DOMAINES_METIER}} = Finance, operations, marketing, produits digitaux
{{CERTIFICATIONS_DIPLOMES}} = A completer
{{ELEMENTS_A_VALORISER}} = analyse de donnees, dashboards, automatisation de reporting, aide a la decision
{{ELEMENTS_A_EVITER}} = postes centres sur data engineering senior, MLOps ou recherche ML

{{REQUETE_DE_RECHERCHE}} = "Data Analyst SQL Power BI Python"
{{LOCALISATION_RECHERCHE}} = Senegal
{{SEUIL_SCORE}} = 4.0
{{MAX_OFFRES_PAR_SOURCE}} = 20

{{JOB_BOARDS_PRIORITAIRES}} =
- job boards locaux ou regionaux pertinents pour le Senegal
- plateformes remote pertinentes pour les profils Data Analyst
- sources generalistes utiles au marche cible lorsque leur integration est faisable

{{JOB_BOARDS_A_RETIRER}} =
- sources uniquement centrees sur le marche francais si elles ne servent pas la recherche ciblee
```
