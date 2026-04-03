"""FluxCD MCP Tools for kagent.

This package provides MCP tools for managing FluxCD GitOps resources including:
- Kustomizations
- GitRepositories
- HelmReleases
- HelmRepositories
- Health and diagnostics
"""

from kagent_tools_flux.tools import (
    # Kustomization tools
    list_kustomizations,
    get_kustomization,
    reconcile_kustomization,
    suspend_kustomization,
    resume_kustomization,
    # GitRepository tools
    list_git_repositories,
    get_git_repository,
    reconcile_git_repository,
    suspend_git_repository,
    resume_git_repository,
    # HelmRelease tools
    list_helm_releases,
    get_helm_release,
    reconcile_helm_release,
    suspend_helm_release,
    resume_helm_release,
    # HelmRepository tools
    list_helm_repositories,
    get_helm_repository,
    # Health and diagnostics
    get_flux_system_status,
    list_failed_reconciliations,
    get_reconciliation_events,
)

__all__ = [
    # Kustomization tools
    "list_kustomizations",
    "get_kustomization",
    "reconcile_kustomization",
    "suspend_kustomization",
    "resume_kustomization",
    # GitRepository tools
    "list_git_repositories",
    "get_git_repository",
    "reconcile_git_repository",
    "suspend_git_repository",
    "resume_git_repository",
    # HelmRelease tools
    "list_helm_releases",
    "get_helm_release",
    "reconcile_helm_release",
    "suspend_helm_release",
    "resume_helm_release",
    # HelmRepository tools
    "list_helm_repositories",
    "get_helm_repository",
    # Health and diagnostics
    "get_flux_system_status",
    "list_failed_reconciliations",
    "get_reconciliation_events",
]

__version__ = "0.1.0"
