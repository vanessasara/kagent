"""FluxCD MCP Tools for managing GitOps resources in Kubernetes.

This module provides tools for interacting with FluxCD resources including
Kustomizations, GitRepositories, HelmReleases, and HelmRepositories.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# Initialize Kubernetes client
try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        logger.warning("Could not load Kubernetes configuration")


# Custom API clients for Flux CRDs
def get_custom_api() -> client.CustomObjectsApi:
    """Get Kubernetes CustomObjectsApi client."""
    return client.CustomObjectsApi()


def get_core_v1_api() -> client.CoreV1Api:
    """Get Kubernetes CoreV1Api client."""
    return client.CoreV1Api()


def get_apps_v1_api() -> client.AppsV1Api:
    """Get Kubernetes AppsV1Api client."""
    return client.AppsV1Api()


# Kustomization Tools

async def list_kustomizations(namespace: Optional[str] = None) -> Dict[str, Any]:
    """List all Kustomization resources.

    Args:
        namespace: Optional namespace to filter results. If not provided, lists cluster-wide.

    Returns:
        Dict containing list of Kustomizations or error information.
    """
    try:
        api = get_custom_api()

        if namespace:
            response = api.list_namespaced_custom_object(
                group="kustomize.toolkit.fluxcd.io",
                version="v1",
                namespace=namespace,
                plural="kustomizations"
            )
        else:
            response = api.list_cluster_custom_object(
                group="kustomize.toolkit.fluxcd.io",
                version="v1",
                plural="kustomizations"
            )

        items = response.get("items", [])
        kustomizations = []

        for item in items:
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            kustomizations.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "ready": _get_ready_condition(status),
                "suspended": spec.get("suspend", False),
                "source": spec.get("sourceRef", {}),
                "last_applied": _get_last_applied_time(status),
            })

        return {
            "success": True,
            "count": len(kustomizations),
            "kustomizations": kustomizations
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_kustomization(name: str, namespace: str) -> Dict[str, Any]:
    """Get details and sync status of a specific Kustomization.

    Args:
        name: Name of the Kustomization
        namespace: Namespace where the Kustomization exists

    Returns:
        Dict containing Kustomization details or error information.
    """
    try:
        api = get_custom_api()

        response = api.get_namespaced_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="kustomizations",
            name=name
        )

        metadata = response.get("metadata", {})
        spec = response.get("spec", {})
        status = response.get("status", {})

        return {
            "success": True,
            "kustomization": {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "spec": {
                    "interval": spec.get("interval"),
                    "path": spec.get("path"),
                    "prune": spec.get("prune"),
                    "source_ref": spec.get("sourceRef", {}),
                    "suspended": spec.get("suspend", False),
                },
                "status": {
                    "ready": _get_ready_condition(status),
                    "conditions": status.get("conditions", []),
                    "last_applied_revision": status.get("lastAppliedRevision"),
                    "last_attempted_revision": status.get("lastAttemptedRevision"),
                    "observed_generation": status.get("observedGeneration"),
                },
            }
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def reconcile_kustomization(name: str, namespace: str) -> Dict[str, Any]:
    """Trigger immediate reconciliation of a Kustomization by annotating it.

    Args:
        name: Name of the Kustomization
        namespace: Namespace where the Kustomization exists

    Returns:
        Dict containing reconciliation trigger result or error information.
    """
    try:
        api = get_custom_api()

        # Add reconcile annotation with current timestamp
        patch = {
            "metadata": {
                "annotations": {
                    "reconcile.fluxcd.io/requestedAt": datetime.utcnow().isoformat() + "Z"
                }
            }
        }

        api.patch_namespaced_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="kustomizations",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"Reconciliation triggered for Kustomization {namespace}/{name}"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def suspend_kustomization(name: str, namespace: str) -> Dict[str, Any]:
    """Suspend reconciliation of a Kustomization.

    Args:
        name: Name of the Kustomization
        namespace: Namespace where the Kustomization exists

    Returns:
        Dict containing suspend result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": True
            }
        }

        api.patch_namespaced_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="kustomizations",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"Kustomization {namespace}/{name} suspended"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def resume_kustomization(name: str, namespace: str) -> Dict[str, Any]:
    """Resume a suspended Kustomization.

    Args:
        name: Name of the Kustomization
        namespace: Namespace where the Kustomization exists

    Returns:
        Dict containing resume result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": False
            }
        }

        api.patch_namespaced_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="kustomizations",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"Kustomization {namespace}/{name} resumed"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


# GitRepository Tools

async def list_git_repositories(namespace: Optional[str] = None) -> Dict[str, Any]:
    """List all GitRepository sources.

    Args:
        namespace: Optional namespace to filter results. If not provided, lists cluster-wide.

    Returns:
        Dict containing list of GitRepositories or error information.
    """
    try:
        api = get_custom_api()

        if namespace:
            response = api.list_namespaced_custom_object(
                group="source.toolkit.fluxcd.io",
                version="v1",
                namespace=namespace,
                plural="gitrepositories"
            )
        else:
            response = api.list_cluster_custom_object(
                group="source.toolkit.fluxcd.io",
                version="v1",
                plural="gitrepositories"
            )

        items = response.get("items", [])
        git_repos = []

        for item in items:
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            git_repos.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "url": spec.get("url"),
                "ref": spec.get("ref", {}),
                "ready": _get_ready_condition(status),
                "suspended": spec.get("suspend", False),
                "artifact": status.get("artifact", {}),
            })

        return {
            "success": True,
            "count": len(git_repos),
            "git_repositories": git_repos
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_git_repository(name: str, namespace: str) -> Dict[str, Any]:
    """Get details, ref, and sync status of a GitRepository.

    Args:
        name: Name of the GitRepository
        namespace: Namespace where the GitRepository exists

    Returns:
        Dict containing GitRepository details or error information.
    """
    try:
        api = get_custom_api()

        response = api.get_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="gitrepositories",
            name=name
        )

        metadata = response.get("metadata", {})
        spec = response.get("spec", {})
        status = response.get("status", {})

        return {
            "success": True,
            "git_repository": {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "spec": {
                    "url": spec.get("url"),
                    "ref": spec.get("ref", {}),
                    "interval": spec.get("interval"),
                    "suspended": spec.get("suspend", False),
                },
                "status": {
                    "ready": _get_ready_condition(status),
                    "conditions": status.get("conditions", []),
                    "artifact": status.get("artifact", {}),
                    "observed_generation": status.get("observedGeneration"),
                },
            }
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def reconcile_git_repository(name: str, namespace: str) -> Dict[str, Any]:
    """Force re-fetch from upstream Git source.

    Args:
        name: Name of the GitRepository
        namespace: Namespace where the GitRepository exists

    Returns:
        Dict containing reconciliation trigger result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "metadata": {
                "annotations": {
                    "reconcile.fluxcd.io/requestedAt": datetime.utcnow().isoformat() + "Z"
                }
            }
        }

        api.patch_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="gitrepositories",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"Reconciliation triggered for GitRepository {namespace}/{name}"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def suspend_git_repository(name: str, namespace: str) -> Dict[str, Any]:
    """Suspend a GitRepository source.

    Args:
        name: Name of the GitRepository
        namespace: Namespace where the GitRepository exists

    Returns:
        Dict containing suspend result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": True
            }
        }

        api.patch_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="gitrepositories",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"GitRepository {namespace}/{name} suspended"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def resume_git_repository(name: str, namespace: str) -> Dict[str, Any]:
    """Resume a suspended GitRepository source.

    Args:
        name: Name of the GitRepository
        namespace: Namespace where the GitRepository exists

    Returns:
        Dict containing resume result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": False
            }
        }

        api.patch_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="gitrepositories",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"GitRepository {namespace}/{name} resumed"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


# HelmRelease Tools

async def list_helm_releases(namespace: Optional[str] = None) -> Dict[str, Any]:
    """List all HelmRelease resources.

    Args:
        namespace: Optional namespace to filter results. If not provided, lists cluster-wide.

    Returns:
        Dict containing list of HelmReleases or error information.
    """
    try:
        api = get_custom_api()

        if namespace:
            response = api.list_namespaced_custom_object(
                group="helm.toolkit.fluxcd.io",
                version="v2",
                namespace=namespace,
                plural="helmreleases"
            )
        else:
            response = api.list_cluster_custom_object(
                group="helm.toolkit.fluxcd.io",
                version="v2",
                plural="helmreleases"
            )

        items = response.get("items", [])
        helm_releases = []

        for item in items:
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            helm_releases.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "chart": spec.get("chart", {}),
                "ready": _get_ready_condition(status),
                "suspended": spec.get("suspend", False),
                "last_deployed": status.get("lastDeployedRevision"),
            })

        return {
            "success": True,
            "count": len(helm_releases),
            "helm_releases": helm_releases
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_helm_release(name: str, namespace: str) -> Dict[str, Any]:
    """Get details, chart version, and status of a HelmRelease.

    Args:
        name: Name of the HelmRelease
        namespace: Namespace where the HelmRelease exists

    Returns:
        Dict containing HelmRelease details or error information.
    """
    try:
        api = get_custom_api()

        response = api.get_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2",
            namespace=namespace,
            plural="helmreleases",
            name=name
        )

        metadata = response.get("metadata", {})
        spec = response.get("spec", {})
        status = response.get("status", {})

        return {
            "success": True,
            "helm_release": {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "spec": {
                    "chart": spec.get("chart", {}),
                    "interval": spec.get("interval"),
                    "suspended": spec.get("suspend", False),
                    "values": spec.get("values", {}),
                },
                "status": {
                    "ready": _get_ready_condition(status),
                    "conditions": status.get("conditions", []),
                    "last_deployed_revision": status.get("lastDeployedRevision"),
                    "last_attempted_revision": status.get("lastAttemptedRevision"),
                    "observed_generation": status.get("observedGeneration"),
                },
            }
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def reconcile_helm_release(name: str, namespace: str) -> Dict[str, Any]:
    """Trigger immediate Helm reconciliation.

    Args:
        name: Name of the HelmRelease
        namespace: Namespace where the HelmRelease exists

    Returns:
        Dict containing reconciliation trigger result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "metadata": {
                "annotations": {
                    "reconcile.fluxcd.io/requestedAt": datetime.utcnow().isoformat() + "Z"
                }
            }
        }

        api.patch_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2",
            namespace=namespace,
            plural="helmreleases",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"Reconciliation triggered for HelmRelease {namespace}/{name}"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def suspend_helm_release(name: str, namespace: str) -> Dict[str, Any]:
    """Suspend a HelmRelease.

    Args:
        name: Name of the HelmRelease
        namespace: Namespace where the HelmRelease exists

    Returns:
        Dict containing suspend result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": True
            }
        }

        api.patch_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2",
            namespace=namespace,
            plural="helmreleases",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"HelmRelease {namespace}/{name} suspended"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def resume_helm_release(name: str, namespace: str) -> Dict[str, Any]:
    """Resume a suspended HelmRelease.

    Args:
        name: Name of the HelmRelease
        namespace: Namespace where the HelmRelease exists

    Returns:
        Dict containing resume result or error information.
    """
    try:
        api = get_custom_api()

        patch = {
            "spec": {
                "suspend": False
            }
        }

        api.patch_namespaced_custom_object(
            group="helm.toolkit.fluxcd.io",
            version="v2",
            namespace=namespace,
            plural="helmreleases",
            name=name,
            body=patch
        )

        return {
            "success": True,
            "message": f"HelmRelease {namespace}/{name} resumed"
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


# HelmRepository Tools

async def list_helm_repositories(namespace: Optional[str] = None) -> Dict[str, Any]:
    """List all HelmRepository sources.

    Args:
        namespace: Optional namespace to filter results. If not provided, lists cluster-wide.

    Returns:
        Dict containing list of HelmRepositories or error information.
    """
    try:
        api = get_custom_api()

        if namespace:
            response = api.list_namespaced_custom_object(
                group="source.toolkit.fluxcd.io",
                version="v1",
                namespace=namespace,
                plural="helmrepositories"
            )
        else:
            response = api.list_cluster_custom_object(
                group="source.toolkit.fluxcd.io",
                version="v1",
                plural="helmrepositories"
            )

        items = response.get("items", [])
        helm_repos = []

        for item in items:
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            spec = item.get("spec", {})

            helm_repos.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "url": spec.get("url"),
                "ready": _get_ready_condition(status),
                "artifact": status.get("artifact", {}),
            })

        return {
            "success": True,
            "count": len(helm_repos),
            "helm_repositories": helm_repos
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_helm_repository(name: str, namespace: str) -> Dict[str, Any]:
    """Get details and last fetch status of a HelmRepository.

    Args:
        name: Name of the HelmRepository
        namespace: Namespace where the HelmRepository exists

    Returns:
        Dict containing HelmRepository details or error information.
    """
    try:
        api = get_custom_api()

        response = api.get_namespaced_custom_object(
            group="source.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="helmrepositories",
            name=name
        )

        metadata = response.get("metadata", {})
        spec = response.get("spec", {})
        status = response.get("status", {})

        return {
            "success": True,
            "helm_repository": {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "spec": {
                    "url": spec.get("url"),
                    "interval": spec.get("interval"),
                    "type": spec.get("type", "default"),
                },
                "status": {
                    "ready": _get_ready_condition(status),
                    "conditions": status.get("conditions", []),
                    "artifact": status.get("artifact", {}),
                    "observed_generation": status.get("observedGeneration"),
                },
            }
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


# Health and Diagnostics Tools

async def get_flux_system_status(namespace: str = "flux-system") -> Dict[str, Any]:
    """Check that all flux-system pods are healthy.

    Args:
        namespace: Namespace where Flux is installed (default: flux-system)

    Returns:
        Dict containing Flux system health status or error information.
    """
    try:
        apps_api = get_apps_v1_api()
        core_api = get_core_v1_api()

        # Get all deployments in flux-system namespace
        deployments = apps_api.list_namespaced_deployment(namespace=namespace)

        deployment_status = []
        all_healthy = True

        for deployment in deployments.items:
            name = deployment.metadata.name
            replicas = deployment.spec.replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0

            is_healthy = ready_replicas == replicas and replicas > 0
            all_healthy = all_healthy and is_healthy

            deployment_status.append({
                "name": name,
                "replicas": replicas,
                "ready": ready_replicas,
                "healthy": is_healthy,
            })

        # Get pod details
        pods = core_api.list_namespaced_pod(namespace=namespace)
        pod_status = []

        for pod in pods.items:
            phase = pod.status.phase
            pod_status.append({
                "name": pod.metadata.name,
                "phase": phase,
                "ready": phase == "Running",
            })

        return {
            "success": True,
            "namespace": namespace,
            "healthy": all_healthy,
            "deployments": deployment_status,
            "pods": pod_status,
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def list_failed_reconciliations(namespace: Optional[str] = None) -> Dict[str, Any]:
    """Find all Flux resources in a failed state.

    Args:
        namespace: Optional namespace to filter results. If not provided, checks cluster-wide.

    Returns:
        Dict containing list of failed resources or error information.
    """
    try:
        failed_resources = []

        # Check Kustomizations
        kustomizations = await list_kustomizations(namespace)
        if kustomizations.get("success"):
            for kustomization in kustomizations.get("kustomizations", []):
                if not kustomization.get("ready"):
                    failed_resources.append({
                        "type": "Kustomization",
                        "name": kustomization.get("name"),
                        "namespace": kustomization.get("namespace"),
                        "ready": False,
                    })

        # Check GitRepositories
        git_repos = await list_git_repositories(namespace)
        if git_repos.get("success"):
            for git_repo in git_repos.get("git_repositories", []):
                if not git_repo.get("ready"):
                    failed_resources.append({
                        "type": "GitRepository",
                        "name": git_repo.get("name"),
                        "namespace": git_repo.get("namespace"),
                        "ready": False,
                    })

        # Check HelmReleases
        helm_releases = await list_helm_releases(namespace)
        if helm_releases.get("success"):
            for helm_release in helm_releases.get("helm_releases", []):
                if not helm_release.get("ready"):
                    failed_resources.append({
                        "type": "HelmRelease",
                        "name": helm_release.get("name"),
                        "namespace": helm_release.get("namespace"),
                        "ready": False,
                    })

        # Check HelmRepositories
        helm_repos = await list_helm_repositories(namespace)
        if helm_repos.get("success"):
            for helm_repo in helm_repos.get("helm_repositories", []):
                if not helm_repo.get("ready"):
                    failed_resources.append({
                        "type": "HelmRepository",
                        "name": helm_repo.get("name"),
                        "namespace": helm_repo.get("namespace"),
                        "ready": False,
                    })

        return {
            "success": True,
            "count": len(failed_resources),
            "failed_resources": failed_resources,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


async def get_reconciliation_events(
    resource_type: str,
    name: str,
    namespace: str,
    limit: int = 10
) -> Dict[str, Any]:
    """Get recent Kubernetes events for a Flux resource.

    Args:
        resource_type: Type of resource (Kustomization, GitRepository, HelmRelease, HelmRepository)
        name: Name of the resource
        namespace: Namespace where the resource exists
        limit: Maximum number of events to return (default: 10)

    Returns:
        Dict containing events or error information.
    """
    try:
        core_api = get_core_v1_api()

        # Get events related to this resource
        field_selector = f"involvedObject.name={name},involvedObject.namespace={namespace}"
        events = core_api.list_namespaced_event(
            namespace=namespace,
            field_selector=field_selector
        )

        # Sort events by timestamp (most recent first)
        sorted_events = sorted(
            events.items,
            key=lambda e: e.last_timestamp or e.event_time or datetime.min,
            reverse=True
        )

        # Limit results
        limited_events = sorted_events[:limit]

        event_list = []
        for event in limited_events:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "first_timestamp": str(event.first_timestamp) if event.first_timestamp else None,
                "last_timestamp": str(event.last_timestamp) if event.last_timestamp else None,
            })

        return {
            "success": True,
            "resource_type": resource_type,
            "name": name,
            "namespace": namespace,
            "count": len(event_list),
            "events": event_list,
        }

    except ApiException as e:
        return {
            "success": False,
            "error": f"Kubernetes API error: {e.status} - {e.reason}",
            "details": str(e.body) if e.body else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


# Helper Functions

def _get_ready_condition(status: Dict[str, Any]) -> bool:
    """Extract the Ready condition from a Flux resource status.

    Args:
        status: Status dict from a Flux resource

    Returns:
        Boolean indicating if the resource is ready
    """
    conditions = status.get("conditions", [])
    for condition in conditions:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


def _get_last_applied_time(status: Dict[str, Any]) -> Optional[str]:
    """Extract the last applied time from a Flux resource status.

    Args:
        status: Status dict from a Flux resource

    Returns:
        Last applied time as a string or None
    """
    conditions = status.get("conditions", [])
    for condition in conditions:
        if condition.get("type") == "Ready":
            return condition.get("lastTransitionTime")
    return None
