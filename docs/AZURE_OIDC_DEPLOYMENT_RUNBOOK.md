# Azure OIDC deployment runbook

## Scope and safety boundary

This runbook prepares an advisory-only staging deployment. It does not authorize
a live Multica connection, production data, blocking enforcement, or a direct
Azure Portal deployment. Use the guarded manual workflow in
`.github/workflows/azure-iac.yml`; do not run `az deployment group create`
locally as an unreviewed substitute.

## Prerequisites

Create separate Azure resource groups and GitHub Environments named `staging`
and `production`. The OIDC application must have one federated credential for
each GitHub Environment, scoped to `Myan17/OpenAI-Hack`.

Assign the application only the reviewed least-privilege role at each resource
group. Do not grant subscription Owner and do not create a client secret.

## GitHub Environment variables

In each GitHub Environment, add these **Variables**, not Actions secrets:

| Variable | Staging value | Production value |
|---|---|---|
| `AZURE_CLIENT_ID` | Entra application client ID | same application client ID |
| `AZURE_TENANT_ID` | Entra directory tenant ID | same tenant ID |
| `AZURE_SUBSCRIPTION_ID` | approved Azure subscription | approved Azure subscription |
| `AZURE_RESOURCE_GROUP` | `rg-interlock-staging` | `rg-interlock-production` |
| `AZURE_LOCATION` | `eastus` | `eastus` |
| `POSTGRES_SERVER_NAME` | approved globally unique staging name | approved globally unique production name |
| `REGISTRY_NAME` | approved globally unique staging name | approved globally unique production name |

The last two values are naming decisions, not secrets. Do not add passwords,
connection strings, certificates, client secrets, callback signatures, or
customer data to GitHub Variables or the repository.

## First staging rehearsal

1. Confirm the `staging` GitHub Environment exists and that its OIDC credential
   exactly targets the repository and environment.
2. In GitHub Actions, choose **Azure infrastructure** → **Run workflow**.
3. Select `staging` and leave `apply` unchecked. This compiles Bicep only.
4. Review the workflow output. Fix template or variable errors before any apply.
5. Schedule a reviewed run with `apply` checked. The workflow runs Azure
   `what-if` immediately before the deployment command.
6. Record the workflow URL, what-if output, deployed resource IDs, and smoke
   test result in the release record.

## Production progression

Production requires a protected GitHub Environment with a required reviewer.
Do not run it until staging is stable, the retained-data and recovery decisions
are approved, and the staging Multica contract is separately authorized.

## Rollback

If the what-if output is unexpected, cancel before approval. If a deployment
causes a suspected cross-tenant issue, disable callback processing, preserve
evidence and workflow logs, suspend the affected workspace, and follow the
incident procedure in `AZURE_MULTITENANT_WATERFALL_EXECUTION_PLAN.md`.
