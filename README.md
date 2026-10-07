# Configurateur Albert

Application qui installe et règle **OpenCode** et/ou **Pi** pour qu'ils utilisent
**Albert API**, l'IA souveraine de l'État, sans taper une seule commande.
Elle ajoute aussi quelques **skills** (savoir-faire) et **MCP** (connecteurs) utiles.

Public visé : enseignant·es et agents publics **sans compétence technique**
(formation DRANE Sarthe).

---

## Pour les collègues : mode d'emploi

### 1. Avant de commencer

- Un compte sur le [Playground Albert](https://albert.playground.etalab.gouv.fr)
  (connexion **ProConnect** avec votre adresse professionnelle).
- Une connexion Internet.
- Aucun droit administrateur n'est nécessaire.

### 2. Télécharger

Page **Releases** du dépôt, puis le fichier de votre système :

| Système | Fichier |
|---|---|
| Windows 10/11 | `ConfigurateurAlbert-Windows.exe` |
| macOS (Apple M1, M2, M3…) | `ConfigurateurAlbert-macOS.zip` (double-cliquer pour décompresser) |
| Linux | `ConfigurateurAlbert-Linux` |

### 3. Ouvrir l'application la première fois

L'application n'est pas signée par Apple ni par Microsoft : votre système affiche
donc un avertissement la première fois. C'est normal.

- **macOS** : double-cliquez sur *ConfigurateurAlbert*. Si macOS refuse de l'ouvrir,
  allez dans **Réglages Système → Confidentialité et sécurité**, descendez jusqu'au
  message concernant ConfigurateurAlbert et cliquez sur **Ouvrir quand même**.
- **Windows** : si « Windows a protégé votre ordinateur » s'affiche, cliquez sur
  **Informations complémentaires**, puis **Exécuter quand même**.
- **Linux** : clic droit → Propriétés → cocher « Autoriser l'exécution », ou bien
  `chmod +x ConfigurateurAlbert-Linux`.

### 4. Suivre les étapes

1. **Diagnostic** de l'ordinateur. Un « ! » orange n'est pas une erreur : l'application s'en occupe.
2. **Clé Albert** : bouton pour ouvrir la page des clés, coller la clé, tester.
3. Choix des **assistants** (OpenCode, Pi) et du **modèle par défaut**.
4. Choix des **skills** puis des **connecteurs**.
5. **Installation** et vérification automatique.

Ensuite : **fermez et rouvrez votre terminal**, placez-vous dans votre dossier de travail
et tapez `opencode` ou `pi`.

Relancer l'application plus tard **répare** ou **met à jour** l'installation
(nouvelle clé, nouveaux modèles…). Le bouton **Désinstaller** de la page d'accueil
retire tout ce qu'elle a ajouté.

### Ce que l'application modifie sur votre ordinateur

| Élément | Emplacement |
|---|---|
| Clé Albert (« coffre ») | macOS/Linux : `~/.albert.env` (lisible par vous seul), chargé par `~/.zshrc` / `~/.bashrc` · Windows : variable de compte `ALBERT_API_KEY` |
| Node.js (si absent ou trop ancien) | copie personnelle dans `~/.local/share/configurateur-albert/node` (Windows : `%LOCALAPPDATA%\configurateur-albert\node`) |
| OpenCode | `~/.config/opencode/opencode.json` (section `albert` seulement) |
| Pi | `~/.pi/agent/models.json`, `settings.json`, `mcp.json` |
| Skills | `~/.agents/skills/` (lu par OpenCode et par Pi) |

Avant chaque modification, une copie datée est faite (`opencode.json.bak-20261007-142501`…).
Vos autres réglages (autres fournisseurs, autres MCP, skills personnels) ne sont jamais touchés.

**La clé n'apparaît dans aucun fichier de réglage** : OpenCode et Pi la lisent dans la
variable d'environnement `ALBERT_API_KEY`. Elle n'est jamais affichée en entier ni écrite
dans le journal. Aucune donnée n'est envoyée ailleurs qu'à Albert API, et l'application
n'envoie aucune télémétrie.

---

## Pour les développeurs

### Lancer depuis les sources

```bash
python3 -m pip install certifi
python3 -m configurateur_albert            # interface graphique
python3 -m configurateur_albert --texte    # mode texte (terminal)
python3 -m configurateur_albert --desinstaller
```

Il faut Python ≥ 3.10 avec Tkinter (fourni par les installeurs de python.org ;
sous Debian/Ubuntu : `sudo apt install python3-tk`).

### Tests

```bash
python3 -m pip install pytest ruff
python3 -m ruff check . && python3 -m pytest -q
```

Les tests utilisent un dossier personnel jetable : ils ne touchent jamais au vrai `$HOME`.

### Construire les exécutables

La CI GitHub Actions (`.github/workflows/build.yml`) lance les tests sur les 3 systèmes,
puis construit les exécutables avec PyInstaller. Pousser une étiquette `v0.1.0` crée un
brouillon de *Release* avec les trois fichiers. En local :

```bash
python3 -m pip install pyinstaller certifi
pyinstaller --noconfirm packaging/configurateur-albert.spec
```

### Architecture

```
configurateur_albert/
  catalog.json   modèles testés/exclus, skills et MCP proposés (à éditer sans toucher au code)
  albert.py      test de la clé, GET /v1/models, sélection des modèles
  keystore.py    coffre de la clé + bloc balisé dans ~/.zshrc / ~/.bashrc
  winenv.py      variables de compte Windows (registre HKCU + WM_SETTINGCHANGE)
  node.py        Node.js LTS « utilisateur » (archive nodejs.org vérifiée en SHA-256)
  configs.py     fusion des configurations OpenCode / Pi (et retrait)
  skills.py      installation dans ~/.agents/skills (archives GitHub ou skills embarqués)
  installer.py   enchaînement des étapes, vérifications, désinstallation
  gui.py         assistant Tkinter    cli.py  mode texte
  skills/        skills maison embarqués
```

### Ajouter un skill ou un MCP

- **Skill maison** : créer `configurateur_albert/skills/<nom>/SKILL.md` (frontmatter
  `name` = nom du dossier, `description` précise), puis l'ajouter à `catalog.json`
  avec `"source": {"type": "bundled"}`.
- **Skill d'un dépôt GitHub** : `"source": {"type": "github", "repo": "org/depot", "ref": "main", "path": "skills/nom"}`.
- **MCP** : entrée `{"type": "remote", "url": …}` ou `{"type": "local", "command": ["npx", "-y", "paquet"]}`
  (sous Windows, `npx` est automatiquement lancé via `cmd /c`).

### Choix techniques

- **Python + Tkinter + PyInstaller** : un seul code pour les trois systèmes, dans un langage
  que l'équipe maîtrise ; Tkinter est inclus dans Python, donc aucune dépendance graphique.
- **Pi : MCP natif** (`~/.pi/agent/mcp.json`) depuis Pi 0.99. L'extension `pi-mcp-adapter`
  n'est plus nécessaire (et, si on l'installe, elle désactive le MCP natif).
- **OpenCode épinglé en v1** (`opencode-ai@1`) : c'est le format de configuration testé.
  Si une v2 est détectée, l'application installe la v1 ; si la v2 reste prioritaire
  (installée par Homebrew par exemple), la configuration n'est pas écrite et l'utilisateur est prévenu.
- **Node.js personnel** quand le Node du système est absent, trop ancien (< 22.19 pour Pi)
  ou demande des droits administrateur pour `npm install -g` (postes d'établissement).
- Modèles proposés **lus en direct** sur `GET /v1/models` (catalogue mouvant), enrichis par les
  métadonnées testées de `catalog.json` ; les modèles inconnus sont déclarés « non testés ».
