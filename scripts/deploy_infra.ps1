param(
  [ValidateSet('dev','prod')]
  [string]$Env = 'dev'

  ,[ValidateSet('plan','apply')]
  [string]$Action = 'plan'

  ,[switch]$AutoApprove

  ,[string]$AwsProfile

  ,[string]$AwsRegion
)

$ErrorActionPreference = 'Stop'

$tfScript = Join-Path $PSScriptRoot 'terraform.ps1'

if ($Action -eq 'apply') {
  & $tfScript -Env $Env -Action apply -AutoApprove:$AutoApprove -AwsProfile $AwsProfile -AwsRegion $AwsRegion
} else {
  & $tfScript -Env $Env -Action plan -AwsProfile $AwsProfile -AwsRegion $AwsRegion
}
