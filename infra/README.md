# Azure infrastructure templates

`main.bicep` is a non-deployed foundation template. It intentionally requires
environment-specific parameters at deployment time and contains no tenant,
credential, DNS, or staging-integration value.

Before applying it, complete the production authorization checklist in
`docs/AZURE_MULTITENANT_WATERFALL_EXECUTION_PLAN.md`, validate the Bicep version
against the approved Azure subscription, and add private networking, Key Vault,
Container Apps, diagnostics, policy assignments, and production sizing through
reviewed modules. Do not deploy this sample directly to production.
