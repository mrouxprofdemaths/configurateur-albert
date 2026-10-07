# Configurateur Albert - lancement depuis PowerShell (Windows).
#
#   irm https://forge.apps.education.fr/rouxpierre-edouard/configurateur-albert/-/raw/v0.2.2/install.ps1 | iex
#
# Mode texte (sans fenetre) : $env:CONFIGURATEUR_TEXTE = "1" avant la commande ci-dessus.
# Autres options : $env:CONFIGURATEUR_ARGS = "--desinstaller" (par exemple).
#
# Ce script :
#   1. installe " uv " (gestionnaire Python) dans un dossier personnel, sans droits admin
#      et sans modifier le PATH ;
#   2. lance le Configurateur Albert (version figee ci-dessous) avec un Python fourni par uv.

# Tout est dans un bloc : sous "irm | iex", rien ne reste dans la session de l'utilisateur.
& {
    $ErrorActionPreference = "Stop"
    # Windows PowerShell 5.1 n'active pas toujours TLS 1.2 par defaut.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    $Ref = if ($env:CONFIGURATEUR_REF) { $env:CONFIGURATEUR_REF } else { "v0.2.2" }
    $Depot = "https://forge.apps.education.fr/rouxpierre-edouard/configurateur-albert"
    # CONFIGURATEUR_SOURCE permet de tester une copie locale (utilise par la CI).
    # Archive de la version sur la Forge des communs numeriques educatifs :
    # etiquette (v0.2.2) ou branche (main).
    $Archive = "$Depot/-/archive/$Ref/$Ref.tar.gz"
    $Source = if ($env:CONFIGURATEUR_SOURCE) { $env:CONFIGURATEUR_SOURCE } `
              else { "configurateur-albert @ $Archive" }
    $UvDir = Join-Path $env:LOCALAPPDATA "configurateur-albert\uv"

    Write-Host ""
    Write-Host "=== Configurateur Albert ($Ref) ==="
    Write-Host ""

    # La version demandee existe-t-elle ? (sinon uv afficherait une erreur 404 incomprehensible)
    if (-not $env:CONFIGURATEUR_SOURCE) {
        try {
            Invoke-WebRequest -Uri $Archive -Method Head -UseBasicParsing | Out-Null
        } catch {
            Write-Host "Erreur : la version $Ref du Configurateur Albert est introuvable sur la Forge"
            Write-Host "(etiquette pas encore publiee, ou connexion a forge.apps.education.fr bloquee)."
            Write-Host ""
            Write-Host "Prevenez la personne qui vous a transmis cette commande. Pour essayer la version"
            Write-Host "en cours de developpement :"
            Write-Host "  `$env:CONFIGURATEUR_REF = `"main`"; irm $Depot/-/raw/main/install.ps1 | iex"
            return
        }
    }

    $Uv = Join-Path $UvDir "uv.exe"
    if (-not (Test-Path $Uv)) {
        $existing = Get-Command uv -ErrorAction SilentlyContinue
        if ($existing) {
            $Uv = $existing.Source
        } else {
            Write-Host "Preparation (une seule fois) : telechargement de l'outil uv..."
            New-Item -ItemType Directory -Force -Path $UvDir | Out-Null
            $env:UV_UNMANAGED_INSTALL = $UvDir
            $installer = Invoke-RestMethod "https://github.com/astral-sh/uv/releases/latest/download/uv-installer.ps1"
            Invoke-Expression $installer | Out-Null
            Remove-Item Env:\UV_UNMANAGED_INSTALL
        }
    }
    if (-not (Test-Path $Uv)) {
        Write-Host "Erreur : l'installation de uv a echoue. Verifiez la connexion Internet puis relancez."
        return
    }

    # Python " gere " par uv : il contient Tkinter (la fenetre graphique).
    $env:UV_PYTHON_PREFERENCE = "only-managed"

    # Arguments : ceux du script (execution d'un fichier), ou le mode texte demande par variable.
    $AppArgs = @($args)
    if ($env:CONFIGURATEUR_TEXTE -eq "1") { $AppArgs += "--texte" }
    if ($env:CONFIGURATEUR_ARGS) { $AppArgs += ($env:CONFIGURATEUR_ARGS -split " " | Where-Object { $_ }) }

    $quiet = $AppArgs | Where-Object { $_ -in @("--texte", "--cli", "--desinstaller", "--version", "--test-interface") }
    if (-not $quiet) {
        Write-Host "La fenetre de l'installateur va s'ouvrir (premier lancement : 1 a 2 minutes)."
        Write-Host "Laissez cette fenetre PowerShell ouverte pendant toute l'installation."
        Write-Host ""
    }

    # Sous PowerShell 5.1, la sortie d'erreur d'un programme redirigee devient une erreur
    # PowerShell : avec "Stop", un simple message de uv interromprait tout.
    $ErrorActionPreference = "Continue"
    & $Uv tool run --quiet --python 3.12 --from $Source configurateur-albert @AppArgs
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Host ""
        Write-Host "L'installateur s'est arrete avec une erreur (code $LASTEXITCODE)."
    }
} @args
