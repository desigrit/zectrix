# Open the Raspberry Pi controller through an SSH tunnel.
param([Parameter(Mandatory=$true)][string]$Target)
$controllerUrl = 'http://127.0.0.1:29176'
Write-Host "When SSH connects, open $controllerUrl in your browser. Keep this terminal open."
ssh -N -L 29176:127.0.0.1:29174 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 $Target
