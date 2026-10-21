# apu-llm installer for Windows. Run in PowerShell:
#   irm https://raw.githubusercontent.com/yago-mendoza/apu-llm/main/install.ps1 | iex
#
# 1. Python, if missing (winget).
# 2. The apu command (pip, user scope).
# 3. pip's user Scripts folder on your PATH, so `apu` works in every new terminal.
# 4. apu setup: Ollama, the integrated-GPU switch, the right model for your RAM, Claude Code hookup.
#    It asks before each step.

$ErrorActionPreference = 'Stop'
function Say($m) { Write-Host "`n> $m" -ForegroundColor Cyan }

Say 'Python'
$py = Get-Command python -ErrorAction SilentlyContinue
# The Microsoft Store stub answers to `python` but is not Python: it only opens the Store.
if (-not $py -or $py.Source -like '*WindowsApps*') {
    Write-Host 'Python not found; installing Python 3.13 with winget.'
    winget install --id Python.Python.3.13 -e --silent --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
}
python --version

Say 'apu'
python -m pip install --user --upgrade --quiet --no-warn-script-location git+https://github.com/yago-mendoza/apu-llm
if ($LASTEXITCODE -ne 0) {
    # No git on the machine: pip cannot clone, so take the zip of the main branch instead.
    python -m pip install --user --upgrade --quiet --no-warn-script-location https://github.com/yago-mendoza/apu-llm/archive/refs/heads/main.zip
}

Say 'PATH'
$scripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $scripts) {
    [Environment]::SetEnvironmentVariable('Path', ($userPath.TrimEnd(';') + ";$scripts"), 'User')
    Write-Host "Added $scripts to your PATH (new terminals will see it)."
} else {
    Write-Host "$scripts is already on your PATH."
}
$env:Path += ";$scripts"

Say 'apu setup'
apu setup
