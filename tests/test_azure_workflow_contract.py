"""The Azure workflow must remain manual, OIDC-based, and explicitly guarded."""

from pathlib import Path


def test_azure_workflow_requires_explicit_apply_and_oidc() -> None:
    workflow = Path(".github/workflows/azure-iac.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "id-token: write" in workflow
    assert "if: ${{ inputs.apply }}" in workflow
    assert "uses: azure/login@v2" in workflow
    assert "az deployment group what-if" in workflow
    assert "az deployment group create" in workflow
    assert "client-secret" not in workflow.lower()
