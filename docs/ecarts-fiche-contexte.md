# Écarts entre la fiche de contexte (6/10/2026) et ce qui a été vérifié (7/10/2026)

Vérifications faites dans les paquets publiés (npm) et les dépôts sources, pas sur un poste réel.

| Point de la fiche | Constat | Choix retenu dans l'application |
|---|---|---|
| « Pi — pas de MCP natif, il faut pi-mcp-adapter » | Pi ≥ 0.99 (1.0.4 actuel) a un **MCP natif** : `~/.pi/agent/mcp.json`, `pi mcp add/list`, `/mcp`. `pi-mcp-adapter` désactive ce MCP natif quand il est installé. | MCP natif, écrit dans `~/.pi/agent/mcp.json`. Pas d'extension. Vérifié : `pi mcp list` lit l'entrée générée. |
| « OpenCode v2 existe depuis septembre 2026 » | Sur npm, le tag `latest` d'`opencode-ai` est encore **1.18.35** ; la v2 n'apparaît que sous des tags `beta`/`dev`. | Installation de `opencode-ai@1` (épinglé). Si une v2 est détectée et reste prioritaire, la configuration n'est pas écrite. |
| `"samplingParams": { "tool_choice": "auto" }` pour Pi | Documenté dans `docs/models.md` de Pi 1.0.4 (paramètres libres transmis à l'API). | Ajouté à chaque modèle sauf l'OCR. |
| Paquet Pi `@earendil-works/pi-coding-agent` | Confirmé (l'ancien `@mariozechner/...` s'arrête à 0.73.1). | Si une version < 1.0 est détectée, l'ancien paquet est désinstallé puis le nouveau installé. |
| Extension VS Code | Identifiant `sst-dev.opencode` (lu dans le code source d'OpenCode). | `code --install-extension sst-dev.opencode`, en option. |
| Skills lus par les deux outils | `~/.agents/skills/` confirmé dans les docs de Pi 1.0.4 et d'OpenCode. | Dossier cible unique. |

Validé de bout en bout dans un conteneur Linux (HOME jetable) : Node.js personnel, `npm install -g`
d'OpenCode 1.18.35 et Pi 1.0.4, configurations relues par `opencode models albert` et
`pi --list-models albert`. **Non testé** : les appels réels à Albert (réseau bloqué dans le
conteneur), Windows et macOS réels.
