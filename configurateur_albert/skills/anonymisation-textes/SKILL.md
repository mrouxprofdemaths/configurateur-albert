---
name: anonymisation-textes
description: Anonymise un texte (copie d'élève, compte rendu, courriel, appréciation) en remplaçant noms, prénoms, adresses, dates de naissance, numéros et autres données personnelles par des étiquettes neutres, avant tout traitement par l'IA. À utiliser dès qu'un document peut contenir des informations sur une personne identifiable.
---

# Anonymiser un texte

Objectif : produire une version du texte dans laquelle **aucune personne n'est identifiable**,
tout en gardant le sens utile au travail demandé.

## Règle de départ

Si l'utilisateur colle directement un texte contenant des données nominatives d'élèves,
rappeler brièvement qu'il vaut mieux anonymiser **avant** l'envoi à toute IA, même sur une
plateforme de l'État, puis anonymiser quand même ce qui a été reçu.

## Méthode

1. Lire le texte en entier.
2. Repérer et remplacer, de façon **cohérente** (même personne → même étiquette) :
   - noms et prénoms → `[ÉLÈVE 1]`, `[ÉLÈVE 2]`, `[PARENT 1]`, `[ENSEIGNANT·E 1]`… ;
   - surnoms, initiales, adresses électroniques, identifiants ENT → `[IDENTIFIANT]` ;
   - adresses postales, villes de résidence → `[ADRESSE]`, `[VILLE]` ;
   - dates de naissance, âges précis → `[DATE]`, `[ÂGE]` ;
   - numéros (téléphone, INE, sécurité sociale, dossier) → `[NUMÉRO]` ;
   - nom de l'établissement et de la classe si cela permet d'identifier quelqu'un → `[ÉTABLISSEMENT]`, `[CLASSE]` ;
   - informations sensibles (santé, handicap, situation familiale, origine, religion, sanctions) :
     les **retirer** ou les remplacer par `[INFORMATION SENSIBLE RETIRÉE]` sauf si l'utilisateur
     explique qu'elles sont indispensables à la tâche.
3. Vérifier les identifications **indirectes** (« la fille du maire », « le seul élève redoublant »)
   et les reformuler de façon neutre.
4. Rendre :
   - le texte anonymisé ;
   - un tableau de correspondance `étiquette → catégorie` **sans les vraies valeurs** ;
   - la liste des passages ambigus à vérifier par l'utilisateur.

## Si le texte est dans un fichier

- Ne jamais modifier le fichier d'origine.
- Écrire le résultat dans un nouveau fichier suffixé `-anonymise` (ex. `copie-anonymise.md`).

## Limites à rappeler

L'anonymisation automatique peut oublier des éléments : l'utilisateur doit relire le résultat
avant de l'utiliser ailleurs.
