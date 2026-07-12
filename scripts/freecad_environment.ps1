Set-StrictMode -Version Latest

function Resolve-FreeCADBin {
    [CmdletBinding()]
    param([string]$ExplicitPath = "")

    $candidates = @()
    if ($ExplicitPath) {
        $item = Get-Item -LiteralPath $ExplicitPath -ErrorAction SilentlyContinue
        if ($item) {
            $candidates += $(if ($item.PSIsContainer) { $item.FullName } else { $item.DirectoryName })
        } else {
            $candidates += $ExplicitPath
        }
    }
    if ($env:FREECAD_BIN) {
        $candidates += $env:FREECAD_BIN
    }

    foreach ($commandName in @("FreeCADCmd.exe", "FreeCAD.exe")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            $candidates += Split-Path -Parent $command.Source
        }
    }

    $candidates += @(
        "C:\Program Files\FreeCAD 1.1\bin",
        "D:\Program Files\FreeCAD 1.1\bin",
        "C:\Program Files\FreeCAD 1.0\bin",
        "D:\Program Files\FreeCAD 1.0\bin"
    )

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not $candidate) { continue }
        $binPath = [System.IO.Path]::GetFullPath($candidate)
        if ((Test-Path -LiteralPath (Join-Path $binPath "FreeCAD.exe")) -or
            (Test-Path -LiteralPath (Join-Path $binPath "FreeCADCmd.exe"))) {
            return $binPath
        }
    }

    throw "FreeCAD bin directory not found. Set FREECAD_BIN or pass an explicit executable path."
}
function Resolve-FreeCADExecutable {
    [CmdletBinding()]
    param(
        [ValidateSet("GUI", "Cmd", "Python")]
        [string]$Kind,
        [string]$ExplicitPath = ""
    )

    if ($ExplicitPath -and (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
        return (Get-Item -LiteralPath $ExplicitPath).FullName
    }

    $binPath = Resolve-FreeCADBin -ExplicitPath $ExplicitPath
    $names = switch ($Kind) {
        "GUI" { @("FreeCAD.exe") }
        "Cmd" { @("FreeCADCmd.exe", "freecadcmd.exe") }
        "Python" { @("python.exe") }
    }
    foreach ($name in $names) {
        $candidate = Join-Path $binPath $name
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    throw "FreeCAD $Kind executable not found under: $binPath"
}
