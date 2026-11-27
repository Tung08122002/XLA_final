<#
.SYNOPSIS
Chạy tuần tự pipeline trên Windows PowerShell.

.DESCRIPTION
Mặc định giữ nguyên bộ dữ liệu đã kèm theo. Dùng -RebuildDataset chỉ khi thật sự
muốn tạo lại data/images. t08/t10 đo thời gian nên luôn chạy tuần tự.

.EXAMPLE
.\run_all.ps1
.\run_all.ps1 -SkipOcr
.\run_all.ps1 -RebuildDataset
#>
[CmdletBinding()]
param(
    [switch]$RebuildDataset,
    [switch]$SkipOcr,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
$env:PYTHONUTF8 = "1"
if (-not $Python) {
    $ProjectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $ProjectPython -PathType Leaf) {
        $Python = $ProjectPython
    } else {
        $Python = "python"
    }
}
Write-Host "Python: $Python"

$verifyArgs = @("src\verify_environment.py")
if (-not $SkipOcr) { $verifyArgs += "--require-ocr" }
if ($RebuildDataset) { $verifyArgs += "--require-font" }

Write-Host "=== Kiểm tra môi trường ==="
& $Python @verifyArgs
if ($LASTEXITCODE -ne 0) {
    throw "Môi trường chưa sẵn sàng. Xem các dòng [THIẾU] ở trên."
}

if ($RebuildDataset) {
    Write-Host "=== src\make_dataset.py ==="
    & $Python "src\make_dataset.py"
    if ($LASTEXITCODE -ne 0) { throw "Lỗi: src\make_dataset.py" }
} else {
    Write-Host "=== Giữ nguyên data/images có sẵn (không tái tạo dữ liệu) ==="
}

$tasks = @(
    "t01_dataset_analysis.py",
    "t02_worked_example.py",
    "t03_baseline.py",
    "t04_webp_vs_baseline.py",
    "t05_rd_bdrate.py",
    "t06_isoquality_recommend.py",
    "t07_text_readability.py",
    "t08_ablation.py",
    "t09_failure_cases.py",
    "t10_timing.py"
)
if ($SkipOcr) {
    $tasks = $tasks | Where-Object { $_ -notin @("t07_text_readability.py", "t09_failure_cases.py") }
    Write-Warning "Bỏ t07 và t09 vì -SkipOcr đã được chọn."
}

foreach ($task in $tasks) {
    Write-Host "=== src\$task ==="
    & $Python (Join-Path "src" $task)
    if ($LASTEXITCODE -ne 0) { throw "Lỗi: src\$task" }
}

Write-Host "Hoàn tất pipeline. Kết quả nằm trong results\ và figures\."
