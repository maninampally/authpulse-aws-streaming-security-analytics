param(
  [Parameter(Mandatory = $false)]
  [string]$Message,

  [Parameter(Mandatory = $false)]
  [switch]$SkipTests,

  [Parameter(Mandatory = $false)]
  [switch]$All,

  [Parameter(Mandatory = $false)]
  [string[]]$Paths = @(),

  [Parameter(Mandatory = $false)]
  [switch]$NoVerify,

  [Parameter(Mandatory = $false)]
  [switch]$Amend
)

$ErrorActionPreference = 'Stop'

function Invoke-Git {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Args
  )

  & git @Args
  if ($LASTEXITCODE -ne 0) {
    throw "git failed: git $($Args -join ' ')"
  }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'git is not available on PATH.'
}

$inside = (& git rev-parse --is-inside-work-tree 2>$null)
if ($LASTEXITCODE -ne 0 -or $inside -ne 'true') {
  throw 'Not inside a git repository.'
}

$repoRoot = (& git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
  throw 'Unable to determine repo root.'
}

if ([string]::IsNullOrWhiteSpace($Message)) {
  throw 'Provide a commit message via -Message (non-interactive safe).'
}

Push-Location $repoRoot
try {
  if (-not $SkipTests) {
    $testScript = Join-Path $repoRoot 'scripts\run_tests.ps1'
    if (-not (Test-Path $testScript)) {
      throw "Test script not found: $testScript"
    }

    & $testScript
    if ($LASTEXITCODE -ne 0) {
      throw 'Tests failed; aborting commit.'
    }
  }

  $status = (& git status --porcelain)
  if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read git status.'
  }

  if ((-not $Amend) -and [string]::IsNullOrWhiteSpace(($status | Out-String).Trim())) {
    Write-Host 'No working tree changes to commit.'
    exit 0
  }

  $doStage = $All -or ($Paths.Count -gt 0)
  if ((-not $doStage) -and (-not $Amend)) {
    throw 'Specify what to stage via -All or -Paths (or use -Amend for message-only amend).'
  }

  if ($doStage) {
    if ($All) {
      Invoke-Git -Args @('add', '-A')
    }
    else {
      Invoke-Git -Args (@('add', '--') + $Paths)
    }
  }

  $staged = (& git diff --cached --name-only)
  if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read staged changes.'
  }

  if ((-not $Amend) -and [string]::IsNullOrWhiteSpace(($staged | Out-String).Trim())) {
    Write-Host 'Nothing staged; nothing to commit.'
    exit 0
  }

  $commitArgs = @('commit', '-m', $Message)
  if ($Amend) {
    $commitArgs += '--amend'
  }
  if ($NoVerify) {
    $commitArgs += '--no-verify'
  }

  Invoke-Git -Args $commitArgs

  $last = (& git log -1 --oneline)
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Committed: $last"
  }
}
finally {
  Pop-Location
}
