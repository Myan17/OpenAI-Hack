# Public staging demo deployment

## Purpose

This is a time-boxed public demonstration deployment for Interlock. It serves the static Next.js dashboard and FastAPI service from one Azure Container App using Azure's managed public hostname. It is not a production, multi-tenant, or customer-data deployment.

## Explicit boundaries

- No Azure PostgreSQL resource, customer data, tenant onboarding, or retention store is created.
- No OpenAI API key is deployed. The policy-draft action therefore fails closed to a deny-all policy if an operator tries it; the deterministic simulator and safety demo remain available.
- No live Multica API, webhook, credential, callback, or external agent effect is enabled.
- The app uses local fixture state inside its container. Restarting or scaling the revision discards that state.
- GitHub Actions authenticates to Azure with the existing Entra federated credential and OIDC; no client secret is stored.

## Prerequisites

The `staging` GitHub Environment needs only these Variables:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP=rg-interlock-staging
AZURE_LOCATION=eastus
```

The `interlock-github-deploy` service principal needs the Azure **Contributor** role scoped to `rg-interlock-staging`.

## Deploy

1. Push the deployment workflow to `main`.
2. In GitHub, open **Actions** → **Deploy public Interlock demo** → **Run workflow**.
3. Select `staging`, set `deploy` to `true`, and run it.
4. Wait for the workflow to print an `https://…azurecontainerapps.io` URL.
5. Open that URL and run **Run safety demo**. Do not use the live agent or claim an external integration.

Azure Container Apps creates a managed public FQDN for external ingress, so a custom domain and DNS are unnecessary for the submission. The workflow uses `az containerapp up` to build the included Dockerfile, create/update the staging Container App, and print its hostname.

## Operational notes

- The first deployment can take several minutes because Azure provisions a Container Apps environment and builds the image.
- The workflow has no automatic trigger and only runs when `deploy: true` is selected.
- If deployment fails, preserve the GitHub Actions logs and do not repeatedly retry. The local demo remains the fallback.
- Delete staging resources after the hackathon if you do not want to incur charges.
