# Sets Windows Created / Modified / Accessed dates for the 9 quotation files.
# Run in the folder that contains the files (close them in Excel first).
$d = Get-Date "2026-09-27 12:06"

$files = @(
  "Al Awael _(IML4L21)_(100).xlsx",
  "Al Jabr RAC _(IML4L39)_(100).xlsx",
  "Al Jomaih _(IML4L02)_(100).xlsx",
  "Al Sharhan _(IML4L39)_(100).xlsx",
  "Key RAC _(IML4L39)_(150).xlsx",
  "Madarat Al Wast _(IML4L02)_(100).xlsx",
  "Sadd Al Manar _(IML4L21)_(100).xlsx",
  "Saudi hala_(IML4L21)_(100).xlsx",
  "Winch Logistics _(IML4L39)_(50).xlsx"
)

foreach ($name in $files) {
  $path = Join-Path (Get-Location) $name
  if (Test-Path -LiteralPath $path) {
    $f = Get-Item -LiteralPath $path
    $f.CreationTime   = $d
    $f.LastWriteTime  = $d
    $f.LastAccessTime = $d
    Write-Host "Updated: $name" -ForegroundColor Green
  } else {
    Write-Host "NOT FOUND: $name" -ForegroundColor Red
  }
}

Get-ChildItem -LiteralPath . -File -Filter *.xlsx | Format-Table Name, CreationTime, LastWriteTime -AutoSize
