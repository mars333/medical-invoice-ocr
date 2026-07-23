$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Dist = Join-Path $Root "dist\medical-invoice-excel"
$Models = Join-Path $Dist "models"
$OfficialModels = Join-Path `
  ([Environment]::GetFolderPath("UserProfile")) `
  ".paddlex\official_models"
$DetectionModel = Join-Path $OfficialModels "PP-OCRv6_medium_det"
$RecognitionModel = Join-Path $OfficialModels "PP-OCRv6_medium_rec"

if (-not (Test-Path -LiteralPath $DetectionModel)) {
  throw "未找到检测模型：$DetectionModel。请先运行一次应用完成模型下载。"
}
if (-not (Test-Path -LiteralPath $RecognitionModel)) {
  throw "未找到识别模型：$RecognitionModel。请先运行一次应用完成模型下载。"
}

& $Python -m pip install pyinstaller
& $Python -m PyInstaller --noconfirm --clean (Join-Path $Root "medical_invoice_ocr.spec")

New-Item -ItemType Directory -Force -Path $Models | Out-Null
Copy-Item -Recurse -Force -LiteralPath $DetectionModel -Destination $Models
Copy-Item -Recurse -Force -LiteralPath $RecognitionModel -Destination $Models
Copy-Item -Force (Join-Path $Root "README.md") (Join-Path $Dist "使用说明.md")

Write-Host "Build completed: $Dist"
