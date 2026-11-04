# Grava dados historicos a partir da porta serial do ESP32.
# Executar na raiz do repositorio ou a partir de qualquer pasta:
#   .\scripts\gravar_historico.ps1 COM5
#
# Requisito: pip install -r scripts/requirements-serial.txt

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Porta
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

python scripts/serial_grava_csv.py --port $Porta
