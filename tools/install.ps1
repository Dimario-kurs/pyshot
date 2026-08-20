#Requires -Version 5.1
<#
    Установка PyShot.

    По умолчанию — в C:\Program Files\PyShot, то есть для всех пользователей
    компьютера. Такая папка защищена системой: удалить её без прав
    администратора нельзя, случайно снести программу не получится.
    Скрипт сам запросит повышение прав (появится окно UAC).

    Ключ -PerUser ставит программу только для текущего пользователя в
    %LOCALAPPDATA%\Programs\PyShot — без UAC.
#>

[CmdletBinding()]
param(
    [switch]$PerUser,           # установка только для текущего пользователя
    [switch]$NoLaunch,          # не запускать программу после установки
    [switch]$DesktopShortcut,   # дополнительно положить ярлык на рабочий стол
    [string]$SourceExe          # служебный: путь к exe после повышения прав
)

$ErrorActionPreference = 'Stop'

$AppName   = 'PyShot'
$AppTitle  = 'PyShot — скриншоты'
$Version   = '1.0.0'
$Publisher = 'Dimario-kurs'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-Step($text) { Write-Host "  $text" }

# --- где взять exe (ищем до повышения прав: путь передадим дальше) --------
$candidates = @(
    $SourceExe,
    (Join-Path $here "$AppName.exe"),
    (Join-Path $root "dist\$AppName.exe"),
    (Join-Path $root "$AppName.exe")
)
$source = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $source) {
    Write-Host "Не найден $AppName.exe." -ForegroundColor Red
    Write-Host "Соберите его через tools\build_exe.bat или положите рядом со скриптом."
    exit 1
}
$source = (Resolve-Path $source).Path

# --- при установке для всех нужны права администратора -------------------
if (-not $PerUser -and -not (Test-Admin)) {
    Write-Host ""
    Write-Host "Для установки в Program Files нужны права администратора." -ForegroundColor Yellow
    Write-Host "Сейчас появится запрос Windows — нажмите «Да»."
    Write-Host ""

    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass',
                   '-File', ('"{0}"' -f $MyInvocation.MyCommand.Path),
                   '-SourceExe', ('"{0}"' -f $source))
    if ($NoLaunch)         { $arguments += '-NoLaunch' }
    if ($DesktopShortcut)  { $arguments += '-DesktopShortcut' }
    try {
        Start-Process -FilePath 'powershell.exe' -Verb RunAs `
                      -ArgumentList $arguments -Wait
    } catch {
        Write-Host "Установка отменена: права администратора не выданы." -ForegroundColor Red
        exit 1
    }
    exit 0
}

if ($PerUser) {
    $targetDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
    $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    $hive      = 'HKCU:'
    $scopeName = 'для текущего пользователя'
} else {
    $targetDir = Join-Path $env:ProgramFiles $AppName
    $startMenu = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'
    $hive      = 'HKLM:'
    $scopeName = 'для всех пользователей'
}
$targetExe = Join-Path $targetDir "$AppName.exe"

Write-Host ""
Write-Host "Установка $AppTitle $Version ($scopeName)" -ForegroundColor Cyan
Write-Host ""
Write-Step "Файл: $source"

# --- закрыть запущенную копию --------------------------------------------
$running = Get-Process -Name $AppName -ErrorAction SilentlyContinue
if ($running) {
    Write-Step 'Закрываю запущенную копию…'
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# --- убрать прежнюю установку в профиле пользователя ---------------------
if (-not $PerUser) {
    $oldDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
    $oldKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
    $oldLnk = Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs') "$AppName.lnk"
    if ((Test-Path $oldDir) -or (Test-Path $oldKey)) {
        Remove-Item -LiteralPath $oldLnk -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $oldKey -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $oldDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Step 'Прежняя копия из профиля пользователя удалена'
    }
}

# --- копирование ----------------------------------------------------------
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -LiteralPath $source -Destination $targetExe -Force
Copy-Item -LiteralPath (Join-Path $here 'uninstall.ps1') `
          -Destination (Join-Path $targetDir 'uninstall.ps1') -Force
Write-Step "Установлено в: $targetDir"

# --- ярлык в меню «Пуск» --------------------------------------------------
$shortcut = Join-Path $startMenu "$AppName.lnk"
$shell    = New-Object -ComObject WScript.Shell
$link     = $shell.CreateShortcut($shortcut)
$link.TargetPath       = $targetExe
$link.WorkingDirectory = $targetDir
$link.IconLocation     = "$targetExe,0"
$link.Description      = $AppTitle
$link.Save()
Write-Step 'Ярлык добавлен в меню «Пуск»'

if ($DesktopShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $link2 = $shell.CreateShortcut((Join-Path $desktop "$AppName.lnk"))
    $link2.TargetPath       = $targetExe
    $link2.WorkingDirectory = $targetDir
    $link2.IconLocation     = "$targetExe,0"
    $link2.Description      = $AppTitle
    $link2.Save()
    Write-Step 'Ярлык добавлен на рабочий стол'
}

# --- запись для «Установки и удаления программ» ---------------------------
$uninstallKey = "$hive\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
$uninstallCmd = ('powershell -NoProfile -ExecutionPolicy Bypass ' +
                 '-File "{0}\uninstall.ps1"' -f $targetDir)
$sizeKb = [math]::Round((Get-Item $targetExe).Length / 1KB)

New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name 'DisplayName'          -Value $AppTitle
Set-ItemProperty -Path $uninstallKey -Name 'DisplayVersion'       -Value $Version
Set-ItemProperty -Path $uninstallKey -Name 'Publisher'            -Value $Publisher
Set-ItemProperty -Path $uninstallKey -Name 'DisplayIcon'          -Value $targetExe
Set-ItemProperty -Path $uninstallKey -Name 'InstallLocation'      -Value $targetDir
Set-ItemProperty -Path $uninstallKey -Name 'UninstallString'      -Value $uninstallCmd
Set-ItemProperty -Path $uninstallKey -Name 'QuietUninstallString' -Value $uninstallCmd
Set-ItemProperty -Path $uninstallKey -Name 'InstallDate'          -Value (Get-Date -Format 'yyyyMMdd')
Set-ItemProperty -Path $uninstallKey -Name 'EstimatedSize' -Value $sizeKb -Type DWord
Set-ItemProperty -Path $uninstallKey -Name 'NoModify' -Value 1 -Type DWord
Set-ItemProperty -Path $uninstallKey -Name 'NoRepair' -Value 1 -Type DWord
Write-Step 'Программа видна в «Установке и удалении программ»'

# --- автозапуск остаётся личной настройкой пользователя ------------------
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$existing = Get-ItemProperty -Path $runKey -Name $AppName -ErrorAction SilentlyContinue
if ($existing) {
    Set-ItemProperty -Path $runKey -Name $AppName -Value ('"{0}"' -f $targetExe)
    Write-Step 'Автозапуск переключён на установленную копию'
}

Write-Host ""
Write-Host "Готово." -ForegroundColor Green
Write-Host "Программа: $targetExe"
Write-Host "Удаление:  Параметры → Приложения → PyShot → Удалить"
Write-Host ""

if (-not $NoLaunch) {
    # запускаем от обычного пользователя, а не с правами администратора
    Start-Process -FilePath (Join-Path $env:WINDIR 'explorer.exe') `
                  -ArgumentList ('"{0}"' -f $targetExe)
    Write-Host "PyShot запущен — значок появился в области уведомлений."
    Write-Host ""
}
