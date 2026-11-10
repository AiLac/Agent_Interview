$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$outDir = Join-Path $projectRoot 'out'
$distDir = Join-Path $projectRoot 'dist'
New-Item -ItemType Directory -Force -Path $outDir, $distDir | Out-Null
$sourceFiles = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'src/demo') -Filter '*.java' | ForEach-Object { $_.FullName })
& javac --release 17 -encoding UTF-8 -d $outDir $sourceFiles
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& jar --create --file (Join-Path $distDir 'mock-google-mcp.jar') --main-class demo.McpServer -C $outDir .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'Built dist/mock-google-mcp.jar'
