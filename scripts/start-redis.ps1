$redisExe = "D:\Tools\MemuraiExtract\Memurai\memurai.exe"
$config = "D:\Tools\MemuraiData\memurai.conf"
$dataDir = "D:\Tools\MemuraiData"

if (!(Test-Path $redisExe)) {
  Write-Error "Redis-compatible executable not found: $redisExe"
  exit 1
}

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

if (!(Test-Path $config)) {
  @"
port 6379
bind 127.0.0.1
protected-mode yes
dir D:/Tools/MemuraiData
databases 16
save 900 1
save 300 10
save 60 10000
appendonly no
"@ | Set-Content -Path $config -Encoding ASCII
}

$existing = Get-NetTCPConnection -LocalPort 6379 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) {
  Write-Host "Redis-compatible service is already listening on 127.0.0.1:6379."
  exit 0
}

Start-Process -FilePath $redisExe -ArgumentList $config -WorkingDirectory $dataDir -WindowStyle Hidden
Start-Sleep -Seconds 2

$cli = "D:\Tools\MemuraiExtract\Memurai\memurai-cli.exe"
if (Test-Path $cli) {
  & $cli -h 127.0.0.1 -p 6379 ping
}

