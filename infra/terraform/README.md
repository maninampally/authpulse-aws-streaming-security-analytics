# Terraform

This folder contains a Terraform layout split into:

- `envs/dev` and `envs/prod`: thin composition layers
- `modules/*`: reusable building blocks

## State

By default, the envs are compatible with local state.

For real deployments, configure a remote backend (S3 + DynamoDB lock) in `envs/*/backend.tf`.
