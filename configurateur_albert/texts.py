"""Textes affichés à l'utilisateur (partagés par l'interface graphique et le mode texte)."""

WELCOME = """Cette application installe et règle pour vous :

  • OpenCode et/ou Pi, deux assistants d'IA qui travaillent sur vos fichiers ;
  • leur branchement sur Albert API, l'IA souveraine de l'État ;
  • quelques « skills » (savoir-faire) et « MCP » (connecteurs) utiles.

Vous n'aurez aucune commande à taper. Il vous faut seulement :
  • une connexion Internet ;
  • une clé Albert API (on vous guide pour la créer).

Rien n'est envoyé ailleurs qu'à Albert API. Relancer l'application plus tard
permet de réparer ou de mettre à jour l'installation."""

KEY_HELP = """1. Cliquez sur « Ouvrir la page des clés » et connectez-vous avec ProConnect
   (adresse professionnelle).
2. Créez une clé, puis copiez-la : elle commence par sk-eyJ… et n'est affichée qu'une fois.
3. Collez-la ci-dessous, puis cliquez sur « Tester la clé ».

La clé sera rangée dans un « coffre » sur ce poste, jamais dans les fichiers de réglages.
Ne la collez jamais dans une conversation avec une IA, un mail ou une capture d'écran."""

MCP_WARNING = ("Chaque connecteur ajoute des informations au contexte du modèle : "
               "n'en choisissez que peu (les quotas d'Albert sont limités).")

USAGE = """Pour utiliser votre assistant :

  1. Fermez tous vos terminaux ouverts (et VS Code), puis rouvrez-en un.
  2. Placez-vous dans le dossier de travail, par exemple :
         cd Documents/MonDossier
  3. Tapez « opencode » ou « pi », puis écrivez votre demande en français.

Dans OpenCode : /models pour changer de modèle, Ctrl+C pour quitter.
Dans Pi : /model pour changer de modèle, @fichier pour citer un fichier,
Ctrl+C deux fois pour quitter.

OCR (Pi) : pi --model albert/lightonocr-2-1b @scan.png "Recopie le texte."
"""

TROUBLESHOOTING = [
    ("401 « Invalid API key »", "Clé mal copiée ou terminal ouvert avant l'installation : rouvrez le terminal ; sinon relancez l'application avec une nouvelle clé."),
    ("Commande introuvable", "Le terminal était ouvert avant l'installation : fermez-le et rouvrez-le."),
    ("« Exécution de scripts désactivée »", "Windows : relancez l'application (elle règle PowerShell) ou demandez au support informatique."),
    ("404 « Model not found »", "Modèle retiré : relancez l'application, elle relit la liste des modèles disponibles."),
    ("429", "Quota par minute atteint : attendez une minute ou changez de modèle."),
    ("503 « Model is too busy »", "Albert est saturé : réessayez plus tard ou changez de modèle."),
    ("L'assistant ne lit pas les fichiers", "Changez de modèle (gemma-4-31b-it conseillé) ; relancez l'application pour réparer les réglages."),
]

STATUS_ICONS = {"ok": "✅", "erreur": "❌", "attention": "⚠️", "ignoré": "➖", "en cours": "⏳", "": "·"}
