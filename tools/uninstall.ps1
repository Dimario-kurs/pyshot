#Requires -Version 5.1
<#
    Удаление PyShot. Запускается из «Параметров → Приложения» или вручную.

    Если программа стоит в Program Files, скрипт сам запросит права
    администратора. Настройки в %APPDATA%\PyShot и снятые скриншоты
    намеренно остаются на месте.
#>

[CmdletBinding()]
param()

$AppName   = 'PyShot'
$here      = Split-Path -Parent $MyInvocation.MyCommand.Path
$programDir = Join-Path $env:ProgramFiles $AppName
$userDir    = Join-Path $env:LOCALAPPDATA "Programs\$AppName"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

# --- установка для всех требует прав администратора ----------------------
$needsAdmin = (Test-Path $programDir) -or
              (Test-Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName")
if ($needsAdmin -and -not (Test-Admin)) {
    # копируем себя во временную папку: удаляемую папку нельзя занимать
    $temp = Join-Path $env:TEMP "$AppName-uninstall.ps1"
    Copy-Item -LiteralPath $MyInvocation.MyCommand.Path -Destination $temp -Force
    try {
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $temp))
    } catch {
        Write-Host "Удаление отменено: права администратора не выданы." -ForegroundColor Red
        exit 1
    }
    exit 0
}

$ErrorActionPreference = 'SilentlyContinue'

# закрыть программу
Get-Process -Name $AppName -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# автозапуск пользователя
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (Get-ItemProperty -Path $runKey -Name $AppName -ErrorAction SilentlyContinue) {
    Remove-ItemProperty -Path $runKey -Name $AppName
}

# ярлыки: общий, личный и на рабочем столе
$shortcuts = @(
    (Join-Path (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs') "$AppName.lnk"),
    (Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs') "$AppName.lnk"),
    (Join-Path ([Environment]::GetFolderPath('Desktop')) "$AppName.lnk")
)
foreach ($lnk in $shortcuts) { Remove-Item -LiteralPath $lnk -Force }

# записи в списке программ — обе на всякий случай
foreach ($hive in @('HKLM:', 'HKCU:')) {
    Remove-Item -Path "$hive\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName" `
                -Recurse -Force
}

# папки удаляем отдельным процессом: этот скрипт может лежать внутри
foreach ($dir in @($programDir, $userDir)) {
    if (Test-Path -LiteralPath $dir) {
        Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden -ArgumentList @(
            '/c', 'timeout /t 2 /nobreak >nul & rmdir /s /q "' + $dir + '"')
    }
}
