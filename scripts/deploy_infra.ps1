param(
  [ValidateSet('dev','prod')]
  [string]$Env = 'dev'
)

$ErrorActionPreference = 'Stop'

Push-Location "infra/terraform/envs/$Env"
try {
  terraform init
  terraform apply
} finally {
  Pop-Location
}
