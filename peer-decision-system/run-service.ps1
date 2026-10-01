param([Parameter(Mandatory=$true)][ValidateSet('backend','frontend')][string]$Service)
$ErrorActionPreference = 'Stop'
$serviceDirectory = Join-Path $PSScriptRoot $Service
Set-Location -LiteralPath $serviceDirectory
$env:PYTHONUTF8 = '1'
if ($Service -eq 'backend') {
    $executable = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $arguments = @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000')
} else {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    $executable = if ($nodeCommand) { $nodeCommand.Source } else { Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
    $env:PATH = (Split-Path -Parent $executable) + [IO.Path]::PathSeparator + $env:PATH
    $arguments = @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173')
}
$process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $serviceDirectory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $serviceDirectory "$Service.stdout.log") -RedirectStandardError (Join-Path $serviceDirectory "$Service.stderr.log") -PassThru
$process.WaitForExit()
exit $process.ExitCode
