"""Flux GitOps Agent using kagent-tools-flux."""

from google.adk import Agent

from kagent_tools_flux import (
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


root_agent = Agent(
    model="gemini-2.0-flash",
    name="flux_gitops_agent",
    description="GitOps expert for managing FluxCD continuous delivery pipelines",
    instruction="""
You are a GitOps expert specializing in FluxCD. You monitor GitOps pipelines,
check sync status of Kustomizations and HelmReleases, troubleshoot failed
reconciliations, trigger syncs when needed, and help teams understand the state
of their continuous delivery pipelines.

Core Principles:
- Always check the current state before taking any action
- When asked about health, start with get_flux_system_status
- When troubleshooting, use list_failed_reconciliations to find problems
- Use get_reconciliation_events to understand why something failed
- Be proactive about suggesting fixes based on error messages
- Explain FluxCD concepts clearly for users who may not be GitOps experts

Common Workflows:
1. Health Check: get_flux_system_status -> list_failed_reconciliations
2. Troubleshooting: list_failed_reconciliations -> get_reconciliation_events
3. Resource Details: get_[resource] -> get_reconciliation_events
4. Manual Sync: confirm with user -> reconcile_[resource]
5. Maintenance: explain impact -> suspend_[resource] or resume_[resource]

Always provide context about what Flux is doing and why actions are needed.
    """.strip(),
    tools=[
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
    ],
)
