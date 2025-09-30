# script_build.ps1
# Usage: .\script_build.ps1

$script   = "script.py"
$outname  = "script"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "❌ PyInstaller not found. Run: pip install pyinstaller"
    exit 1
}

Remove-Item -Recurse -Force "build","dist","$outname.spec" -ErrorAction SilentlyContinue

Write-Host "🚀 Building $script → dist\$outname\... (onedir mode)"
pyinstaller `
  --name script `
  --noconsole `
  --clean `
  --log-level=DEBUG `
  --strip `
  --exclude-module tkinter `
  --exclude-module _tkinter `
  --exclude-module tk `
  --exclude-module tcl `
  --collect-submodules pygetwindow `
  --collect-submodules pyautogui `
  --collect-submodules psutil `
  --collect-submodules win32process `
  script.py


if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build finished successfully. EXE at: dist\$outname\$outname.exe"
    Write-Host "ℹ️ Onedir mode start เร็ว แต่ต้อง copy ทั้งโฟลเดอร์ dist\$outname\ ไปใช้งาน"
} else {
    Write-Error "❌ Build failed with exit code $LASTEXITCODE"
}
