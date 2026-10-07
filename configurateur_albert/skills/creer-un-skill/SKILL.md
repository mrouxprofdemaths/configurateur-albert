---
name: creer-un-skill
description: Aide l'utilisateur à créer son propre skill (un mode d'emploi réutilisable que l'assistant consultera ensuite tout seul), par exemple pour rédiger une fiche de séance, appliquer une méthode pédagogique ou respecter un modèle de document de l'établissement. À utiliser quand l'utilisateur dit « crée un skill », « je fais souvent la même chose », « retiens cette méthode » ou « je voudrais que tu fasses toujours comme ça ».
---

# Créer un skill

Un **skill** est un dossier contenant un fichier `SKILL.md` : un mode d'emploi que l'assistant
lit quand une demande correspond à sa description. OpenCode et Pi lisent tous les deux les
skills rangés dans `~/.agents/skills/`.

Parlez simplement : l'utilisateur n'est pas informaticien. Ne lui demandez jamais d'écrire
du code ni d'utiliser le terminal ; c'est vous qui créez les fichiers.

## 1. Comprendre le besoin (3 à 5 questions, une à la fois)

1. **Quelle tâche** le skill doit-il aider à faire ? (ex. « rédiger une fiche de séance »)
2. **Quand** doit-il servir ? Quelles phrases l'utilisateur emploiera-t-il pour le demander ?
3. **Comment** la tâche doit-elle être faite : étapes, règles, pièges à éviter ?
4. **À quoi** ressemble un bon résultat ? Demandez un exemple réussi (texte collé ou nom de fichier).
5. Y a-t-il un **modèle** à respecter (plan imposé, rubriques, mise en forme) ?

S'il a déjà un document qui décrit sa méthode, lisez-le plutôt que de poser toutes les questions.

## 2. Choisir le nom

- 1 à 64 caractères : **minuscules sans accents, chiffres et tirets** uniquement ;
  pas de tiret au début, à la fin, ni deux tirets de suite.
- Le nom du dossier doit être **identique** au champ `name`.
- Exemples valides : `fiche-seance`, `methode-actif`, `bulletin-appreciations`.

## 3. Écrire le fichier

Créez `~/.agents/skills/<nom>/SKILL.md` (sous Windows : `%USERPROFILE%\.agents\skills\<nom>\SKILL.md`) :

```markdown
---
name: <nom>
description: <Ce que fait le skill ET quand l'utiliser, avec les mots que l'utilisateur
  emploiera. 1 à 3 phrases, 1 024 caractères au maximum.>
---

# <Titre lisible>

## Quand l'utiliser
…

## Méthode
1. …
2. …

## Règles à respecter
- …

## Exemple de résultat attendu
…
```

Conseils :

- **La description est décisive** : c'est elle seule que l'assistant voit avant d'ouvrir le
  skill. « Aide pour les fiches » est trop vague ; « Rédige une fiche de séance de
  mathématiques au format de l'établissement (objectifs, déroulé minuté, différenciation).
  À utiliser pour toute demande de fiche ou de préparation de séance » est efficace.
- Restez **court** (moins de 200 lignes) : les modèles d'Albert ont une mémoire de travail
  limitée. Mettez les longs documents de référence dans un fichier à part, dans le même
  dossier (ex. `modele.md`), et indiquez dans le skill quand le lire.
- Écrivez des **consignes concrètes** (« commence par les objectifs », « 55 minutes au total »)
  plutôt que des généralités.
- Pas de données personnelles d'élèves dans un skill, même en exemple : utilisez des
  exemples fictifs.

## 4. Vérifier avec l'utilisateur

1. Relisez-lui le skill (en résumé) et demandez s'il faut corriger quelque chose.
2. Expliquez-lui qu'il faut **quitter puis relancer** OpenCode ou Pi pour que le nouveau
   skill soit pris en compte.
3. Proposez une phrase de test, par exemple : « Prépare une fiche de séance sur … »,
   et suggérez de l'améliorer ensuite au fil de l'usage (« ajoute au skill que … »).

## Modifier un skill existant

Lisez d'abord le `SKILL.md` existant, faites la modification demandée, et conservez le même
nom. Ne modifiez pas les skills installés par le Configurateur Albert (dossiers contenant le
fichier `.installe-par-configurateur-albert`) : ils seraient remplacés à la prochaine mise à
jour. Proposez plutôt d'en créer une copie sous un autre nom.
