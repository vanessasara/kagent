"""Unit tests for Flux MCP tools.

These tests use mocked Kubernetes clients to test all tool functions
without requiring a real cluster.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from kubernetes.client.rest import ApiException

from kagent_tools_flux import tools


@pytest.fixture
def mock_custom_api():
    """Mock Kubernetes CustomObjectsApi."""
    with patch("kagent_tools_flux.tools.get_custom_api") as mock:
        yield mock.return_value


@pytest.fixture
def mock_core_v1_api():
    """Mock Kubernetes CoreV1Api."""
    with patch("kagent_tools_flux.tools.get_core_v1_api") as mock:
        yield mock.return_value


@pytest.fixture
def mock_apps_v1_api():
    """Mock Kubernetes AppsV1Api."""
    with patch("kagent_tools_flux.tools.get_apps_v1_api") as mock:
        yield mock.return_value


# Kustomization Tests

@pytest.mark.asyncio
async def test_list_kustomizations_success(mock_custom_api):
    """Test listing Kustomizations successfully."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "test-kustomization", "namespace": "flux-system"},
                "spec": {"suspend": False, "sourceRef": {"kind": "GitRepository", "name": "flux-system"}},
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}]
                },
            }
        ]
    }

    result = await tools.list_kustomizations()

    assert result["success"] is True
    assert result["count"] == 1
    assert len(result["kustomizations"]) == 1
    assert result["kustomizations"][0]["name"] == "test-kustomization"
    assert result["kustomizations"][0]["ready"] is True


@pytest.mark.asyncio
async def test_list_kustomizations_with_namespace(mock_custom_api):
    """Test listing Kustomizations in a specific namespace."""
    mock_custom_api.list_namespaced_custom_object.return_value = {
        "items": []
    }

    result = await tools.list_kustomizations(namespace="test-namespace")

    assert result["success"] is True
    assert result["count"] == 0
    mock_custom_api.list_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_list_kustomizations_api_error(mock_custom_api):
    """Test handling API errors when listing Kustomizations."""
    mock_custom_api.list_cluster_custom_object.side_effect = ApiException(status=404, reason="Not Found")

    result = await tools.list_kustomizations()

    assert result["success"] is False
    assert "Kubernetes API error" in result["error"]


@pytest.mark.asyncio
async def test_get_kustomization_success(mock_custom_api):
    """Test getting a specific Kustomization successfully."""
    mock_custom_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "test-kustomization", "namespace": "flux-system"},
        "spec": {
            "interval": "5m",
            "path": "./clusters/production",
            "prune": True,
            "sourceRef": {"kind": "GitRepository", "name": "flux-system"},
            "suspend": False,
        },
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "lastAppliedRevision": "main@sha1:abc123",
            "observedGeneration": 1,
        },
    }

    result = await tools.get_kustomization("test-kustomization", "flux-system")

    assert result["success"] is True
    assert result["kustomization"]["name"] == "test-kustomization"
    assert result["kustomization"]["spec"]["interval"] == "5m"
    assert result["kustomization"]["status"]["ready"] is True


@pytest.mark.asyncio
async def test_reconcile_kustomization_success(mock_custom_api):
    """Test triggering Kustomization reconciliation."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.reconcile_kustomization("test-kustomization", "flux-system")

    assert result["success"] is True
    assert "Reconciliation triggered" in result["message"]
    mock_custom_api.patch_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_suspend_kustomization_success(mock_custom_api):
    """Test suspending a Kustomization."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.suspend_kustomization("test-kustomization", "flux-system")

    assert result["success"] is True
    assert "suspended" in result["message"]


@pytest.mark.asyncio
async def test_resume_kustomization_success(mock_custom_api):
    """Test resuming a Kustomization."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.resume_kustomization("test-kustomization", "flux-system")

    assert result["success"] is True
    assert "resumed" in result["message"]


# GitRepository Tests

@pytest.mark.asyncio
async def test_list_git_repositories_success(mock_custom_api):
    """Test listing GitRepositories successfully."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "flux-system", "namespace": "flux-system"},
                "spec": {
                    "url": "https://github.com/example/repo",
                    "ref": {"branch": "main"},
                    "suspend": False,
                },
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "artifact": {"revision": "main@sha1:abc123"},
                },
            }
        ]
    }

    result = await tools.list_git_repositories()

    assert result["success"] is True
    assert result["count"] == 1
    assert result["git_repositories"][0]["name"] == "flux-system"
    assert result["git_repositories"][0]["url"] == "https://github.com/example/repo"


@pytest.mark.asyncio
async def test_get_git_repository_success(mock_custom_api):
    """Test getting a specific GitRepository."""
    mock_custom_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "flux-system", "namespace": "flux-system"},
        "spec": {
            "url": "https://github.com/example/repo",
            "ref": {"branch": "main"},
            "interval": "1m",
            "suspend": False,
        },
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "artifact": {"revision": "main@sha1:abc123"},
        },
    }

    result = await tools.get_git_repository("flux-system", "flux-system")

    assert result["success"] is True
    assert result["git_repository"]["spec"]["url"] == "https://github.com/example/repo"


@pytest.mark.asyncio
async def test_reconcile_git_repository_success(mock_custom_api):
    """Test triggering GitRepository reconciliation."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.reconcile_git_repository("flux-system", "flux-system")

    assert result["success"] is True
    assert "Reconciliation triggered" in result["message"]


@pytest.mark.asyncio
async def test_suspend_git_repository_success(mock_custom_api):
    """Test suspending a GitRepository."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.suspend_git_repository("flux-system", "flux-system")

    assert result["success"] is True
    assert "suspended" in result["message"]


@pytest.mark.asyncio
async def test_resume_git_repository_success(mock_custom_api):
    """Test resuming a GitRepository."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.resume_git_repository("flux-system", "flux-system")

    assert result["success"] is True
    assert "resumed" in result["message"]


# HelmRelease Tests

@pytest.mark.asyncio
async def test_list_helm_releases_success(mock_custom_api):
    """Test listing HelmReleases successfully."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "my-app", "namespace": "default"},
                "spec": {
                    "chart": {"spec": {"chart": "my-chart", "version": "1.0.0"}},
                    "suspend": False,
                },
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "lastDeployedRevision": "1.0.0",
                },
            }
        ]
    }

    result = await tools.list_helm_releases()

    assert result["success"] is True
    assert result["count"] == 1
    assert result["helm_releases"][0]["name"] == "my-app"


@pytest.mark.asyncio
async def test_get_helm_release_success(mock_custom_api):
    """Test getting a specific HelmRelease."""
    mock_custom_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "my-app", "namespace": "default"},
        "spec": {
            "chart": {"spec": {"chart": "my-chart", "version": "1.0.0"}},
            "interval": "5m",
            "suspend": False,
            "values": {"replicaCount": 3},
        },
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "lastDeployedRevision": "1.0.0",
        },
    }

    result = await tools.get_helm_release("my-app", "default")

    assert result["success"] is True
    assert result["helm_release"]["spec"]["values"]["replicaCount"] == 3


@pytest.mark.asyncio
async def test_reconcile_helm_release_success(mock_custom_api):
    """Test triggering HelmRelease reconciliation."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.reconcile_helm_release("my-app", "default")

    assert result["success"] is True
    assert "Reconciliation triggered" in result["message"]


@pytest.mark.asyncio
async def test_suspend_helm_release_success(mock_custom_api):
    """Test suspending a HelmRelease."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.suspend_helm_release("my-app", "default")

    assert result["success"] is True
    assert "suspended" in result["message"]


@pytest.mark.asyncio
async def test_resume_helm_release_success(mock_custom_api):
    """Test resuming a HelmRelease."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await tools.resume_helm_release("my-app", "default")

    assert result["success"] is True
    assert "resumed" in result["message"]


# HelmRepository Tests

@pytest.mark.asyncio
async def test_list_helm_repositories_success(mock_custom_api):
    """Test listing HelmRepositories successfully."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [
            {
                "metadata": {"name": "bitnami", "namespace": "flux-system"},
                "spec": {"url": "https://charts.bitnami.com/bitnami"},
                "status": {
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "artifact": {"revision": "sha256:abc123"},
                },
            }
        ]
    }

    result = await tools.list_helm_repositories()

    assert result["success"] is True
    assert result["count"] == 1
    assert result["helm_repositories"][0]["name"] == "bitnami"


@pytest.mark.asyncio
async def test_get_helm_repository_success(mock_custom_api):
    """Test getting a specific HelmRepository."""
    mock_custom_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "bitnami", "namespace": "flux-system"},
        "spec": {
            "url": "https://charts.bitnami.com/bitnami",
            "interval": "10m",
            "type": "default",
        },
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "artifact": {"revision": "sha256:abc123"},
        },
    }

    result = await tools.get_helm_repository("bitnami", "flux-system")

    assert result["success"] is True
    assert result["helm_repository"]["spec"]["url"] == "https://charts.bitnami.com/bitnami"


# Health and Diagnostics Tests

@pytest.mark.asyncio
async def test_get_flux_system_status_success(mock_apps_v1_api, mock_core_v1_api):
    """Test getting Flux system status."""
    # Mock deployment
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "source-controller"
    mock_deployment.spec.replicas = 1
    mock_deployment.status.ready_replicas = 1

    mock_deployments = MagicMock()
    mock_deployments.items = [mock_deployment]
    mock_apps_v1_api.list_namespaced_deployment.return_value = mock_deployments

    # Mock pods
    mock_pod = MagicMock()
    mock_pod.metadata.name = "source-controller-abc123"
    mock_pod.status.phase = "Running"

    mock_pods = MagicMock()
    mock_pods.items = [mock_pod]
    mock_core_v1_api.list_namespaced_pod.return_value = mock_pods

    result = await tools.get_flux_system_status()

    assert result["success"] is True
    assert result["healthy"] is True
    assert len(result["deployments"]) == 1
    assert result["deployments"][0]["healthy"] is True


@pytest.mark.asyncio
async def test_get_flux_system_status_unhealthy(mock_apps_v1_api, mock_core_v1_api):
    """Test getting Flux system status when unhealthy."""
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "source-controller"
    mock_deployment.spec.replicas = 1
    mock_deployment.status.ready_replicas = 0

    mock_deployments = MagicMock()
    mock_deployments.items = [mock_deployment]
    mock_apps_v1_api.list_namespaced_deployment.return_value = mock_deployments

    mock_pods = MagicMock()
    mock_pods.items = []
    mock_core_v1_api.list_namespaced_pod.return_value = mock_pods

    result = await tools.get_flux_system_status()

    assert result["success"] is True
    assert result["healthy"] is False


@pytest.mark.asyncio
async def test_list_failed_reconciliations_success(mock_custom_api):
    """Test listing failed reconciliations."""
    # Mock failed Kustomization
    mock_custom_api.list_cluster_custom_object.side_effect = [
        {
            "items": [
                {
                    "metadata": {"name": "failed-kustomization", "namespace": "flux-system"},
                    "spec": {"suspend": False},
                    "status": {"conditions": [{"type": "Ready", "status": "False"}]},
                }
            ]
        },
        {"items": []},  # GitRepositories
        {"items": []},  # HelmReleases
        {"items": []},  # HelmRepositories
    ]

    result = await tools.list_failed_reconciliations()

    assert result["success"] is True
    assert result["count"] == 1
    assert result["failed_resources"][0]["type"] == "Kustomization"
    assert result["failed_resources"][0]["ready"] is False


@pytest.mark.asyncio
async def test_get_reconciliation_events_success(mock_core_v1_api):
    """Test getting reconciliation events."""
    mock_event = MagicMock()
    mock_event.type = "Warning"
    mock_event.reason = "ReconciliationFailed"
    mock_event.message = "Failed to apply manifests"
    mock_event.count = 5
    mock_event.first_timestamp = datetime.now()
    mock_event.last_timestamp = datetime.now()
    mock_event.event_time = None

    mock_events = MagicMock()
    mock_events.items = [mock_event]
    mock_core_v1_api.list_namespaced_event.return_value = mock_events

    result = await tools.get_reconciliation_events(
        "Kustomization",
        "test-kustomization",
        "flux-system"
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["events"][0]["type"] == "Warning"
    assert result["events"][0]["reason"] == "ReconciliationFailed"


# Helper Function Tests

def test_get_ready_condition_true():
    """Test extracting Ready condition when True."""
    status = {
        "conditions": [
            {"type": "Ready", "status": "True"}
        ]
    }
    assert tools._get_ready_condition(status) is True


def test_get_ready_condition_false():
    """Test extracting Ready condition when False."""
    status = {
        "conditions": [
            {"type": "Ready", "status": "False"}
        ]
    }
    assert tools._get_ready_condition(status) is False


def test_get_ready_condition_missing():
    """Test extracting Ready condition when missing."""
    status = {"conditions": []}
    assert tools._get_ready_condition(status) is False


def test_get_last_applied_time():
    """Test extracting last applied time."""
    status = {
        "conditions": [
            {"type": "Ready", "status": "True", "lastTransitionTime": "2026-04-03T10:00:00Z"}
        ]
    }
    result = tools._get_last_applied_time(status)
    assert result == "2026-04-03T10:00:00Z"


def test_get_last_applied_time_missing():
    """Test extracting last applied time when missing."""
    status = {"conditions": []}
    assert tools._get_last_applied_time(status) is None
