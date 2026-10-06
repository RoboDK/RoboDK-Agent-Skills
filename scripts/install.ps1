# Link every skills/<name> in this repo into a local agent's skill directory,
# so edits made here are picked up immediately without copying files around.
#
# Usage:
#   .\scripts\install.ps1                                   # links into ~/.claude/skills (Claude Code)
#   .\scripts\install.ps1 -Target "$HOME\.other-agent\skills"
#   .\scripts\install.ps1 -Copy                              # copy instead of junction

param(
    [string]$Target = "$env:USERPROFILE\.claude\skills",
    [switch]$Copy
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

New-Item -ItemType Directory -Force -Path $Target | Out-Null

Get-ChildItem -Path (Join-Path $repoRoot "skills") -Directory | ForEach-Object {
    $name = $_.Name
    $dest = Join-Path $Target $name

    if (Test-Path $dest) {
        Write-Output "skip (exists): $name"
        return
    }

    if ($Copy) {
        Copy-Item -Recurse -Path $_.FullName -Destination $dest
        Write-Output "copied: $name"
    } else {
        # Junction: no admin/Developer-Mode requirement, unlike New-Item -ItemType SymbolicLink.
        New-Item -ItemType Junction -Path $dest -Target $_.FullName | Out-Null
        Write-Output "linked: $name -> $($_.FullName)"
    }
}

Write-Output "Done. Skills available under: $Target"
