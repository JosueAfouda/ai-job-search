# Analyse du codebase et adaptation du positionnement

## Chaîne complète

1. `main.py` lit les arguments, valide les paramètres essentiels et affiche le CV, le profil, les recherches et les sources.
2. `profile.py` charge et valide le JSON de positionnement. `cv_loader.py` sélectionne le PDF, extrait son texte (`pdftotext`, puis bibliothèque Python) et identifie les compétences du vocabulaire configuré.
3. `pipeline.py` interroge les sources enregistrées, répartit le budget entre les requêtes et isole les erreurs de recherche. En mode sample, il utilise six offres fictives.
4. `fetchers/base.py` récupère le HTML, cherche des `JobPosting` JSON-LD ou suit les liens des annonces. À défaut de données structurées, il utilise le titre et la description de page. Chaque fichier de source fournit son URL de recherche et ses motifs de liens.
5. `normalizer.py` nettoie les champs, limite la description à 12 000 caractères et déduplique les annonces. Le modèle partagé `Job` transporte aussi le mode de travail ; les données originales restent dans `raw`.
6. `pipeline.py` filtre les dates et salaires connus : historique initial de 14 jours et 40 000 EUR/an conservé dans la configuration. Les informations manquantes ne bloquent pas une offre.
7. `scoring.py` demande un score structuré de 1 à 5 au modèle, avec le schéma de `schemas/score.schema.json`, ou utilise les correspondances locales. Des plafonds communs empêchent de qualifier de bonne correspondance un poste hors cible, junior, sans compétence requise ou insuffisamment décrit.
8. `tailoring.py` produit un CV Markdown ; `cover_letter.py` produit une lettre de 1 000 caractères maximum. Le mode local utilise les compétences attestées du CV et évite d'inventer un parcours.
9. Les résultats sont triés et écrits dans le JSON et le rapport Markdown avec les liens des documents. Aucun module ne soumet de candidature ou n'envoie de message.

`llm.py` encapsule les sous-processus Codex, les délais, le fichier temporaire de résultat et le décodage JSON. Il reste inchangé. `utils.py` fournit le nettoyage, les noms de fichiers, la troncature, le masquage des téléphones et la détection textuelle du mode de travail. `models.py` contient les dataclasses partagées.

## Éléments de l'ancien positionnement identifiés

- Nom du PDF « Consultant Data » fixé dans la CLI, le pipeline et le chargeur.
- Requête unique « Data Python ».
- Bonus heuristiques sur Power BI, analytics, forecasting, Azure et le simple mot « consultant », indépendamment du métier réellement proposé et parfois du CV.
- Extraction de mots-clés complétée par des mots fréquents non techniques.
- Résumé local de CV affirmant systématiquement « Consultant Data & IA » et dix années d'expérience.
- Lettre locale réaffirmant Python/SQL/BI/ML et mélangeant exigences de l'offre et compétences du candidat.
- Une seule offre sample positive, centrée sur le consulting data.
- Absence de tri explicite des correspondances et risque d'écrasement des documents de deux annonces partageant entreprise et titre.

Ces comportements ont été remplacés par une cible déclarative, une extraction fondée sur le CV, des requêtes distinctes, des limites communes au scoring local et LLM, et des documents locaux factuels.

## Choix pour le nouveau CV

Les expériences de développement et d'automatisation Python, la migration Excel/VBA, les agents IA, les workflows et les API justifient les trois groupes prioritaires. Le backend Python reste une cible pertinente même sans LLM. Les compétences data et DevOps servent de complément ; les postes de data analyst, BI et data scientist ne constituent plus la cible principale.

Le pays reste la France. À la demande de l'utilisateur, remote, hybride et présentiel sont acceptés. Aucun contrat n'est exclu : CDI et missions peuvent remonter. Le tarif journalier d'une mission freelance n'est plus interprété comme un salaire annuel du fait d'une simple sous-chaîne « an » dans sa description.

Le profil n'est pas inféré automatiquement de toutes les expériences du PDF : cette inférence risquerait de réintroduire le positionnement historique. Le JSON explicite l'intention ; le PDF établit les faits. Un futur changement de métier nécessite de modifier ce JSON et le CV, sans réécrire le pipeline.

## Vérification et limites

La suite locale couvre les métiers pertinents et éloignés, les plafonds LLM, les réponses invalides, l'absence d'appel LLM en mode local, les compétences non attestées, les descriptions courtes, le changement complet de métier, les modalités de travail, le choix du PDF, les recherches multiples, leurs erreurs, les doublons, les documents, les filtres et les options historiques.

Les connecteurs n'ont pas été remplacés : tous sont des lecteurs HTML sans navigateur ni authentification. Les moteurs rendus en JavaScript, les protections antibot, les pages de détail inaccessibles ou les métadonnées incomplètes limitent leur couverture. Les erreurs individuelles de pages de détail restent absorbées par le collecteur existant ; les recherches entièrement vides sont désormais signalées. Les URL et paramètres des sites n'ont pas été validés en direct durant cette adaptation.

Le score local ne comprend pas toutes les nuances d'une annonce, les négations et les exigences obligatoires propres à chaque poste. Les alias d'intitulés restent à compléter pour les formulations atypiques. Le modèle peut mieux apprécier les responsabilités, mais doit respecter les plafonds déterministes et ses documents doivent être relus. Les tests ne prétendent pas mesurer la pertinence sur un corpus d'offres réelles.
