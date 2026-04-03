# kagent-tools-flux

FluxCD MCP tool server for kagent - GitOps continuous delivery tools for managing FluxCD resources in Kubernetes.

## Overview

This package provides MCP (Model Context Protocol) tools for interacting with FluxCD, one of the two major GitOps engines in the Kubernetes ecosystem. FluxCD enables continuous delivery of applications using Git as the source of truth.

## What is FluxCD?

[FluxCD](https://fluxcd.io/) is a CNCF graduated project that automates the deployment of applications to Kubernetes clusters. It continuously monitors Git repositories and Helm repositories, automatically applying changes to your cluster when updates are detected.

## Why This Tool Matters

FluxCD is widely adopted for GitOps workflows, but troubleshooting failed reconciliations, checking sync status, and triggering manual syncs typically requires using the `flux` CLI or directly inspecting Kubernetes resources. This tool server enables kagent agents to:

- Monitor GitOps pipeline health
- Troubleshoot failed reconciliations
- Trigger immediate syncs when needed
- Suspend and resume resources for maintenance
- Provide visibility into the continuous delivery process

## Prerequisites

- FluxCD must be installed in your Kubernetes cluster
- The agent needs RBAC permissions to read and update Flux custom resources
- Kubernetes client configuration must be available (in-cluster or kubeconfig)

## Available Tools

### Kustomization Tools (5)

**list_kustomizations(namespace: Optional[str])**
- List all Kustomization resources cluster-wide or in a specific namespace
- Returns: name, namespace, ready status, suspended state, source reference, last applied time

**get_kustomization(name: str, namespace: str)**
- Get detailed information about a specific Kustomization
- Returns: full spec and status including sync state, applied/attempted revisions, conditions

**reconcile_kustomization(name: str, namespace: str)**
- Trigger immediate reconciliation by adding the `reconcile.fluxcd.io/requestedAt` annotation
- Use when you need to force a sync without waiting for the next interval

**suspend_kustomization(name: str, namespace: str)**
- Suspend reconciliation of a Kustomization
- Useful during maintenance windows or when troubleshooting

**resume_kustomization(name: str, namespace: str)**
- Resume a suspended Kustomization
- Reconciliation will restart according to the configured interval

### GitRepository Tools (5)

**list_git_repositories(namespace: Optional[str])**
- List all GitRepository source resources
- Returns: name, namespace, URL, ref, ready status, artifact information

**get_git_repository(name: str, namespace: str)**
- Get details and sync status of a GitRepository source
- Returns: full spec including URL, ref, interval, and artifact details

**reconcile_git_repository(name: str, namespace: str)**
- Force re-fetch from the upstream Git source
- Triggers immediate fetch without waiting for the interval

**suspend_git_repository(name: str, namespace: str)**
- Suspend a GitRepository source
- Stops automatic fetching from the Git repository

**resume_git_repository(name: str, namespace: str)**
- Resume a suspended GitRepository source

### HelmRelease Tools (5)

**list_helm_releases(namespace: Optional[str])**
- List all HelmRelease resources
- Returns: name, namespace, chart info, ready status, last deployed revision

**get_helm_release(name: str, namespace: str)**
- Get details, chart version, and status of a HelmRelease
- Returns: full spec including chart, values, and deployment status

**reconcile_helm_release(name: str, namespace: str)**
- Trigger immediate Helm reconciliation
- Forces Flux to re-evaluate and potentially upgrade/rollback the release

**suspend_helm_release(name: str, namespace: str)**
- Suspend a HelmRelease
- Stops automatic Helm operations for this release

**resume_helm_release(name: str, namespace: str)**
- Resume a suspended HelmRelease

### HelmRepository Tools (2)

**list_helm_repositories(namespace: Optional[str])**
- List all HelmRepository source resources
- Returns: name, namespace, URL, ready status, artifact

**get_helm_repository(name: str, namespace: str)**
- Get details and last fetch status of a HelmRepository
- Returns: spec with URL, interval, type, and artifact status

### Health and Diagnostics Tools (3)

**get_flux_system_status(namespace: str = "flux-system")**
- Check that all Flux system pods are healthy
- Returns: deployment health, pod status for Flux controllers
- Essential for verifying Flux itself is operational

**list_failed_reconciliations(namespace: Optional[str])**
- Find all Flux resources in a failed state across all types
- Returns: list of failed Kustomizations, GitRepositories, HelmReleases, and HelmRepositories
- Perfect for troubleshooting: "What's broken right now?"

**get_reconciliation_events(resource_type: str, name: str, namespace: str, limit: int = 10)**
- Get recent Kubernetes events for a specific Flux resource
- Returns: event type, reason, message, timestamps
- Essential for debugging why a reconciliation failed

## Example Usage

### Basic Agent Configuration

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: flux-agent
  namespace: kagent
spec:
  description: GitOps expert for managing FluxCD continuous delivery pipelines
  instruction: |
    You are a GitOps expert specializing in FluxCD. You monitor GitOps
    pipelines, check sync status of Kustomizations and HelmReleases,
    troubleshoot failed reconciliations, trigger syncs when needed,
    and help teams understand the state of their continuous delivery
    pipelines. Always check the current state before taking any action.
  tools:
    - type: Python
      python:
        package: kagent-tools-flux
        functions:
          - list_kustomizations
          - get_kustomization
          - reconcile_kustomization
          - suspend_kustomization
          - resume_kustomization
          - list_git_repositories
          - get_git_repository
          - reconcile_git_repository
          - suspend_git_repository
          - resume_git_repository
          - list_helm_releases
          - get_helm_release
          - reconcile_helm_release
          - suspend_helm_release
          - resume_helm_release
          - list_helm_repositories
          - get_helm_repository
          - get_flux_system_status
          - list_failed_reconciliations
          - get_reconciliation_events
  modelConfig:
    name: default-model
```

### Example Interactions

**Checking overall Flux health:**
```
User: Is Flux healthy?
Agent: Let me check the Flux system status...
[Calls get_flux_system_status()]
Agent: All Flux controllers are running:
- source-controller: 1/1 ready
- kustomize-controller: 1/1 ready
- helm-controller: 1/1 ready
- notification-controller: 1/1 ready
```

**Finding what's failing:**
```
User: What's not syncing?
Agent: Let me check for failed reconciliations...
[Calls list_failed_reconciliations()]
Agent: Found 2 failed resources:
1. Kustomization "apps" in namespace "flux-system" - not ready
2. HelmRelease "nginx" in namespace "default" - not ready

Let me get more details...
[Calls get_reconciliation_events() for each]
```

**Triggering a manual sync:**
```
User: Force sync the production kustomization
Agent: I'll trigger an immediate reconciliation...
[Calls reconcile_kustomization("production", "flux-system")]
Agent: Reconciliation triggered. The kustomization will sync immediately instead of waiting for the next interval.
```

**Investigating a specific resource:**
```
User: Why is the nginx helm release failing?
Agent: Let me check the nginx HelmRelease details and events...
[Calls get_helm_release("nginx", "default")]
[Calls get_reconciliation_events("HelmRelease", "nginx", "default")]
Agent: The HelmRelease is failing because:
- Chart version 1.2.0 not found in repository
- Last event: "chart pull error: chart 'nginx' version '1.2.0' not found"
You may need to update the chart version or check the HelmRepository.
```

## Common Troubleshooting Scenarios

This agent can help with:

1. **Pipeline Health Checks**: "Are all my Flux resources syncing successfully?"
2. **Sync Status**: "What version of my app is deployed in production?"
3. **Failed Reconciliations**: "Why isn't my kustomization applying?"
4. **Manual Syncs**: "Force sync this kustomization now"
5. **Maintenance**: "Suspend all HelmReleases in the staging namespace"
6. **Drift Detection**: "Is my cluster in sync with Git?"
7. **Source Issues**: "Is Flux able to fetch from my Git repository?"
8. **Helm Problems**: "Why is this Helm chart failing to install?"

## Error Handling

All tool functions return structured responses with success/failure indicators:

```python
{
    "success": True,
    "kustomizations": [...]
}

# On error:
{
    "success": False,
    "error": "Kubernetes API error: 404 - Not Found",
    "details": "..."
}
```

This ensures the agent can gracefully handle errors and provide meaningful feedback to users.

## RBAC Requirements

The agent's ServiceAccount needs these permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: flux-agent-role
rules:
  # Flux Kustomizations
  - apiGroups: ["kustomize.toolkit.fluxcd.io"]
    resources: ["kustomizations"]
    verbs: ["get", "list", "patch"]

  # Flux Sources
  - apiGroups: ["source.toolkit.fluxcd.io"]
    resources: ["gitrepositories", "helmrepositories"]
    verbs: ["get", "list", "patch"]

  # Flux Helm
  - apiGroups: ["helm.toolkit.fluxcd.io"]
    resources: ["helmreleases"]
    verbs: ["get", "list", "patch"]

  # Kubernetes core resources (for health checks and events)
  - apiGroups: [""]
    resources: ["pods", "events"]
    verbs: ["get", "list"]

  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
```

## Development

### Running Tests

```bash
cd python
uv run pytest ./packages/kagent-tools-flux/tests/ -v
```

All tests use mocked Kubernetes clients and do not require a real cluster.

### Installing Locally

```bash
cd python/packages/kagent-tools-flux
uv pip install -e .
```

## Contributing

This tool follows the kagent contribution guidelines. See [CONTRIBUTING.md](https://github.com/kagent-dev/kagent/blob/main/CONTRIBUTING.md).

## License

Apache 2.0 - See the [LICENSE](https://github.com/kagent-dev/kagent/blob/main/LICENSE) file for details.
