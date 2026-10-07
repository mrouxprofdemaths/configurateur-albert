---
name: transcription-audio
description: Transcrit un enregistrement audio (mp3, wav, m4a ; 20 Mo maximum) en texte ou en sous-titres (srt, vtt) avec le modèle whisper-large-v3 d'Albert API. À utiliser quand l'utilisateur demande de transcrire, retranscrire ou sous-titrer un fichier audio ou un cours enregistré.
---

# Transcrire un fichier audio avec Albert

La clé Albert est dans la variable d'environnement `ALBERT_API_KEY`.
**Ne jamais afficher sa valeur**, ne jamais l'écrire dans un fichier ni dans la réponse :
l'utiliser uniquement à travers la variable, comme ci-dessous.

## 1. Vérifier le fichier

- Il doit exister et peser **20 Mo au plus**. Au-delà, proposer de le découper
  (par exemple avec `ffmpeg -i cours.mp3 -f segment -segment_time 900 -c copy morceau_%02d.mp3`
  si ffmpeg est installé), puis transcrire chaque morceau et assembler les textes dans l'ordre.
- Formats acceptés : mp3, wav, m4a, ogg, webm.

## 2. Lancer la transcription

Choisir `response_format` : `text` (texte brut, par défaut), `srt` ou `vtt` (sous-titres).
Le fichier de sortie porte le même nom que l'audio avec l'extension adaptée.

macOS / Linux / Git Bash :

```bash
curl -sS https://albert.api.etalab.gouv.fr/v1/audio/transcriptions \
  -H "Authorization: Bearer $ALBERT_API_KEY" \
  -F "file=@cours.mp3" -F "model=whisper-large-v3" -F "language=fr" \
  -F "response_format=text" -o cours.txt
```

PowerShell (Windows) — utiliser `curl.exe`, pas l'alias `curl` :

```powershell
curl.exe -sS https://albert.api.etalab.gouv.fr/v1/audio/transcriptions `
  -H "Authorization: Bearer $env:ALBERT_API_KEY" `
  -F "file=@cours.mp3" -F "model=whisper-large-v3" -F "language=fr" `
  -F "response_format=text" -o cours.txt
```

## 3. Contrôler le résultat

- Si le fichier de sortie contient `{"detail": …}`, c'est une erreur : l'expliquer
  (401 = clé refusée, 413 = fichier trop gros, 429 = quota atteint, attendre une minute).
- Sinon, annoncer le nom du fichier créé et proposer, si utile : une mise en forme
  (paragraphes, titres), un résumé, ou une version anonymisée (skill `anonymisation-textes`)
  si des personnes sont nommées.
