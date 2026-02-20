param(
  [ValidateSet('dev','prod')]
  [string]$Env = 'dev',

  [ValidateSet('init','fmt','validate','plan','apply','destroy','output')]
  [string]$Action = 'plan',

  [switch]$AutoApprove,

  [string]$AwsProfile,

  [string]$AwsRegion
)

$ErrorActionPreference = 'Stop'

if ($AwsProfile) {
  $env:AWS_PROFILE = $AwsProfile
}

if ($AwsRegion) {
  $env:AWS_REGION = $AwsRegion
  $env:AWS_DEFAULT_REGION = $AwsRegion
}

function Get-TerraformExe {
  $cmd = Get-Command terraform -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  $packagesRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
  if (Test-Path $packagesRoot) {
    $exe = Get-ChildItem -Path $packagesRoot -Recurse -Filter terraform.exe -ErrorAction SilentlyContinue |
      Select-Object -First 1 -ExpandProperty FullName
    if ($exe) {
      return $exe
    }
  }

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host 'Terraform not found in PATH; installing via winget...'
    winget install --id Hashicorp.Terraform -e --source winget

    if (Test-Path $packagesRoot) {
      $exe = Get-ChildItem -Path $packagesRoot -Recurse -Filter terraform.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
      if ($exe) {
        return $exe
      }
    }
  }

  throw 'Terraform CLI not found. Install Terraform and retry, or restart your shell after installation to refresh PATH.'
}

$tf = Get-TerraformExe
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$envDir = Join-Path $repoRoot (Join-Path 'infra\terraform\envs' $Env)
$envDir = (Resolve-Path $envDir).Path

switch ($Action) {
  'fmt' {
    & $tf "-chdir=$envDir" fmt -recursive
  }
  'validate' {
    & $tf "-chdir=$envDir" validate
  }
  'init' {
    & $tf "-chdir=$envDir" init
  }
  'plan' {
    & $tf "-chdir=$envDir" init
    & $tf "-chdir=$envDir" fmt -recursive
    & $tf "-chdir=$envDir" validate
    & $tf "-chdir=$envDir" plan -out=tfplan
  }
  'apply' {
    & $tf "-chdir=$envDir" init
    if ($AutoApprove) {
      if (Test-Path (Join-Path $envDir 'tfplan')) {
        & $tf "-chdir=$envDir" apply -auto-approve tfplan
      } else {
        & $tf "-chdir=$envDir" apply -auto-approve
      }
    } else {
      if (Test-Path (Join-Path $envDir 'tfplan')) {
        & $tf "-chdir=$envDir" apply tfplan
      } else {
        & $tf "-chdir=$envDir" apply
      }
    }
  }
  'destroy' {
    & $tf "-chdir=$envDir" init
    if ($AutoApprove) {
      & $tf "-chdir=$envDir" destroy -auto-approve
    } else {
      & $tf "-chdir=$envDir" destroy
    }
  }
  'output' {
    & $tf "-chdir=$envDir" output
  }
  default {
    throw "Unknown Action: $Action"
  }
}
