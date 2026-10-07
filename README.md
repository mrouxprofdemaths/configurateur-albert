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

### 2. Lancer l'installateur (méthode conseillée)

Ouvrez un terminal, copiez-y **une seule ligne**, puis appuyez sur Entrée.
La fenêtre de l'installateur s'ouvre ensuite toute seule ; **laissez le terminal ouvert**
jusqu'à la fin.

**macOS** — ouvrez l'application *Terminal* (Launchpad → Autres → Terminal, ou
`Cmd + Espace` puis tapez « Terminal ») et collez :

```bash
curl -LsSf https://raw.githubusercontent.com/mrouxprofdemaths/configurateur-albert/v0.1.0/install.sh | sh
```

**Linux** — ouvrez un terminal et collez la même ligne.

**Windows** — clic droit sur le bouton Démarrer → *Terminal* (ou *Windows PowerShell*),
puis collez :

```powershell
irm https://raw.githubusercontent.com/mrouxprofdemaths/configurateur-albert/v0.1.0/install.ps1 | iex
```

Le premier lancement prend 1 à 2 minutes (téléchargement de l'outil *uv* et d'un Python
privé, rangés dans votre dossier personnel, sans droits administrateur). Cette méthode
n'est pas bloquée par Gatekeeper (macOS) ni par SmartScreen (Windows), car aucun programme
téléchargé n'est ouvert par double-clic.

Variantes :

| Besoin | macOS / Linux | Windows |
|---|---|---|
| Mode texte (sans fenêtre) | `… install.sh \| sh -s -- --texte` | `$env:CONFIGURATEUR_TEXTE = "1"` puis la commande |
| Désinstaller | relancer la commande, bouton **Désinstaller** de la page d'accueil | idem |

### 3. Méthode de secours : exécutable à télécharger

Si le terminal vous est impossible, la page **Releases** du dépôt propose un exécutable :

| Système | Fichier |
|---|---|
| Windows 10/11 | `ConfigurateurAlbert-Windows.exe` |
| macOS (Apple M1, M2, M3…) | `ConfigurateurAlbert-macOS.zip` (double-cliquer pour décompresser) |
| Linux | `ConfigurateurAlbert-Linux` |

Il n'est pas signé par Apple ni par Microsoft : le système affiche un avertissement la
première fois, et un poste d'établissement verrouillé peut le refuser.

- **macOS** : double-cliquez sur *ConfigurateurAlbert*. Si macOS refuse de l'ouvrir,
  allez dans **Réglages Système → Confidentialité et sécurité**, descendez jusqu'au
  message concernant ConfigurateurAlbert et cliquez sur **Ouvrir quand même**.
- **Windows** : si « Windows a protégé votre ordinateur » s'affiche, cliquez sur
  **Informations complémentaires**, puis **Exécuter quand même**. L'antivirus peut aussi
  mettre le fichier en quarantaine (faux positif fréquent avec ce type d'exécutable) :
  préférez alors la méthode du terminal.
- **Linux** : `chmod +x ConfigurateurAlbert-Linux`, puis lancez-le.

### 4. Suivre les étapes de la fenêtre

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
| Outil uv et son Python (méthode du terminal) | `~/.local/share/configurateur-albert/uv` et `~/.cache/uv` (Windows : `%LOCALAPPDATA%\configurateur-albert\uv` et `%LOCALAPPDATA%\uv`) ; non retirés par la désinstallation, supprimables à la main |

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

### Scripts d'amorçage (`install.sh`, `install.ps1`)

Ils installent [uv](https://docs.astral.sh/uv/) dans un dossier privé (`UV_UNMANAGED_INSTALL` :
pas de modification du PATH ni du shell), puis lancent
`uv tool run --python 3.12 --from "configurateur-albert @ <archive de l'étiquette>" configurateur-albert`
avec `UV_PYTHON_PREFERENCE=only-managed` (Python de uv, qui contient Tkinter).

- La version est **figée** dans chaque script (`v0.1.0`) : à chaque nouvelle version, mettre à jour
  `REF`/`$Ref` dans les deux scripts **et** les URL du README, puis créer l'étiquette correspondante.
- `CONFIGURATEUR_SOURCE=<chemin>` lance une copie locale (utilisé par la CI) ;
  `CONFIGURATEUR_REF=<étiquette>` choisit une autre version.
- `install.ps1` est en ASCII pur (compatibilité Windows PowerShell 5.1) et tout son code est dans un
  bloc `& { … }` : sous `irm | iex`, rien ne reste dans la session de l'utilisateur, et il n'appelle
  jamais `exit` (cela fermerait sa fenêtre).

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
