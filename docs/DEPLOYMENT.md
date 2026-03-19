## Deployment and Environments

This document outlines how to deploy the Transaction Risk Platform across environments
and how configuration and secrets should be managed.

### Environments

The repository assumes three primary environments:

- `dev`: development and experimentation
- `stage`: pre-production validation
- `prod`: production

Terraform environment-specific configuration can be provided via `.tfvars` files
and/or dedicated environment directories.

### Terraform structure

The `infra/terraform` directory contains:

- Root module with provider and common locals.
- `envs/dev.tfvars` for development defaults.

You can model additional environments by creating:

```bash
infra/terraform/envs/stage.tfvars
infra/terraform/envs/prod.tfvars
```

Each file should specify:

- `aws_region`
- `project`
- `environment`

The root module can be applied per environment:

```bash
cd infra/terraform
terraform init
terraform plan -var-file="envs/dev.tfvars"
terraform apply -var-file="envs/dev.tfvars"
```

### Secrets and configuration

Runtime configuration is driven by environment variables (see `.env.example`).
For production environments:

- Do **not** commit secrets.
- Configure:
  - `AUTH_SECRET_KEY`
  - Database connection details
  - Redis connection details
  - OTEL exporter configuration (if used)

Recommended pattern on AWS:

- Use AWS Systems Manager Parameter Store or AWS Secrets Manager to store:
  - JWT signing key (`AUTH_SECRET_KEY`)
  - DB credentials
  - Redis credentials
- Inject secrets into the runtime (ECS/EKS/Lambda) via:
  - Task definitions / pod env vars referencing parameters.

Terraform should reference only **parameter names/ARNs** as variables, not raw secrets.

### CI/CD flow (high level)

The CI workflow (`.github/workflows/ci.yml`) currently:

- Lints, formats, and type-checks the code.
- Runs unit tests.
- Spins up Postgres and Redis service containers.
- Runs integration tests (including migrations smoke test and end-to-end flows).

A typical production CI/CD flow would extend this with:

1. **Build images**
   - Build Docker images for each service.
   - Tag with commit SHA and environment tags (e.g., `dev`, `stage`, `prod`).
2. **Push images**
   - Push to a registry such as:
     - Amazon ECR
     - Docker Hub
     - GHCR
3. **Deploy**
   - Trigger Terraform or another deployment mechanism with:
     - Image tags
     - Environment-specific variables

This repository intentionally leaves registry names, credentials, and target
platform configuration as operator-provided values.

### Operator-provided values

To deploy to real environments, operators must provide:

- AWS account, region, and credentials.
- Registry name and credentials (for Docker images).
- Values for:
  - `AUTH_SECRET_KEY` (strong secret per environment)
  - Database and Redis endpoints and credentials
  - OTEL exporter endpoints (if used)
- Any additional environment-specific feature flags or limits.

These should be passed securely (e.g., via CI secrets, parameter store, or
secret manager) and **never** committed to the repository.

