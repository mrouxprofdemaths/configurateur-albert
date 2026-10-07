#!/bin/sh
# Configurateur Albert — lancement depuis le terminal (macOS / Linux).
#
#   curl -LsSf https://raw.githubusercontent.com/mrouxprofdemaths/configurateur-albert/v0.1.0/install.sh | sh
#
# Mode texte (sans fenêtre) :
#   curl -LsSf …/install.sh | sh -s -- --texte
#
# Ce script :
#   1. installe « uv » (gestionnaire Python) dans un dossier personnel, sans droits admin
#      et sans modifier vos fichiers de démarrage du shell ;
#   2. lance le Configurateur Albert (version figée ci-dessous) avec un Python fourni par uv.
set -eu

REF="${CONFIGURATEUR_REF:-v0.1.0}"
REPO="mrouxprofdemaths/configurateur-albert"
# CONFIGURATEUR_SOURCE permet de tester une copie locale (utilisé par la CI).
SOURCE="${CONFIGURATEUR_SOURCE:-configurateur-albert @ https://github.com/$REPO/archive/refs/tags/$REF.tar.gz}"
UV_DIR="$HOME/.local/share/configurateur-albert/uv"

say() { printf '%s\n' "$*"; }

say ""
say "=== Configurateur Albert ($REF) ==="
say ""

if ! command -v curl >/dev/null 2>&1; then
    say "Erreur : la commande « curl » est introuvable. Installez-la puis relancez."
    exit 1
fi

if [ -x "$UV_DIR/uv" ]; then
    UV="$UV_DIR/uv"
elif command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
else
    say "Préparation (une seule fois) : téléchargement de l'outil uv…"
    mkdir -p "$UV_DIR"
    curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-installer.sh" \
        | env UV_UNMANAGED_INSTALL="$UV_DIR" sh >/dev/null
    UV="$UV_DIR/uv"
fi

if [ ! -x "$UV" ]; then
    say "Erreur : l'installation de uv a échoué. Vérifiez la connexion Internet puis relancez."
    exit 1
fi

# Python « géré » par uv : il contient Tkinter (la fenêtre graphique), contrairement
# à certains Python du système (Homebrew, Debian…).
export UV_PYTHON_PREFERENCE=only-managed

case " $* " in
    *" --texte "*|*" --cli "*|*" --desinstaller "*|*" --version "*) ;;
    *)
        say "La fenêtre de l'installateur va s'ouvrir (premier lancement : 1 à 2 minutes)."
        say "Laissez ce terminal ouvert pendant toute l'installation."
        say ""
        ;;
esac

# Sous « curl … | sh », l'entrée standard est le script lui-même : on la rebranche
# sur le terminal pour que le mode texte puisse poser ses questions.
# Le test se fait dans un sous-shell : sous dash, un échec de redirection ferait
# quitter le script entier.
if [ ! -t 0 ] && ( exec </dev/tty ) 2>/dev/null; then
    exec "$UV" tool run --quiet --python 3.12 --from "$SOURCE" configurateur-albert "$@" </dev/tty
else
    exec "$UV" tool run --quiet --python 3.12 --from "$SOURCE" configurateur-albert "$@"
fi
