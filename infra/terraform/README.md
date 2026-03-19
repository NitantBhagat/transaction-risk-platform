## Terraform bootstrap

This directory contains the **Terraform bootstrap** for the Transaction Risk Platform.

It is intentionally minimal and focuses on:

- Defining the AWS provider and shared variables.
- Establishing a place to add service-specific infrastructure in later steps.

### Files

- `main.tf`:
  - Terraform and AWS provider configuration.
  - Shared locals for `project`, `environment`, and `common_tags`.
  - Backend configuration block is left commented for you to adapt (e.g. S3 + DynamoDB).
- `variables.tf`:
  - `aws_region`, `project`, `environment`.
- `outputs.tf`:
  - Echoes `project` and `environment` for quick visibility.
- `envs/dev.tfvars`:
  - Example variable values for a `dev` environment.

### Usage (example)

```bash
cd infra/terraform

# Initialise providers and (once configured) backend
terraform init

# See the execution plan for dev
terraform plan -var-file="envs/dev.tfvars"

# Apply changes (when you are ready)
terraform apply -var-file="envs/dev.tfvars"
```

Service-specific modules and resources (API gateways, compute, databases, Redis, etc.) can be added here later without changing the basic layout.

### Operational notes

In a production environment you will typically:

- Provision managed PostgreSQL and Redis services.
- Store sensitive configuration (e.g., `AUTH_SECRET_KEY`, DB credentials) in a secure secret manager.
- Configure observability (logs and metrics) to scrape each service's `/metrics` endpoint and collect stdout logs.

Those concerns are intentionally left out of this bootstrap and should be added according to your target platform's best practices.

### Environments

You can model multiple environments (e.g., `stage`, `prod`) by adding additional
`*.tfvars` files under `envs/`:

- `envs/stage.tfvars`
- `envs/prod.tfvars`

Each environment file should at minimum set:

- `aws_region`
- `project`
- `environment`

Then reference the appropriate file when planning/applying:

```bash
terraform plan -var-file="envs/stage.tfvars"
terraform apply -var-file="envs/stage.tfvars"
```



