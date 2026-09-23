$Root = Split-Path -Parent $PSScriptRoot
& python (Join-Path $Root "source\nuxpad.py") @args
exit $LASTEXITCODE
