$backend = "D:\PycharmProducts\ns_auto_testing_platfrom\backend"
$logFile = "celery-worker.log"

Set-Location $backend

$existing = Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*celery*config*worker*" } |
  Select-Object -First 1

if ($existing) {
  Write-Host "Celery worker is already running. PID: $($existing.ProcessId)"
  exit 0
}

Start-Process -FilePath celery -ArgumentList "-A config worker --pool=solo --loglevel=info --logfile $logFile" -WorkingDirectory $backend -WindowStyle Hidden
Start-Sleep -Seconds 5
celery -A config inspect ping --timeout=10

