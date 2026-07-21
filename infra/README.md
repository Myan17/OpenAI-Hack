# Azure infrastructure templates

`main.bicep` is a non-deployed foundation template. It intentionally requires
environment-specific parameters at deployment time and contains no tenant,
credential, DNS, or staging-integration value.

`../.github/workflows/azure-iac.yml` compiles the template on manual dispatch.
It can make Azure changes only when an operator chooses `apply: true`, the
selected GitHub Environment permits the job, and the environment contains these
non-secret GitHub Actions variables:

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`
- `POSTGRES_SERVER_NAME`, `REGISTRY_NAME`

The workflow uses GitHub OIDC through `azure/login`; it does not use a client
secret. It runs `what-if` immediately before any explicit apply. Configure
separate `staging` and `production` GitHub Environments, with a required
reviewer on production.

Before applying it, complete the production authorization checklist in
`docs/AZURE_MULTITENANT_WATERFALL_EXECUTION_PLAN.md`, validate the Bicep version
against the approved Azure subscription, and add private networking, Key Vault,
Container Apps, diagnostics, policy assignments, and production sizing through
reviewed modules. Do not deploy this sample directly to production.
