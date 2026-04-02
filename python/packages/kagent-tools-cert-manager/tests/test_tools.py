"""Unit tests for cert-manager tools."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubernetes.client.rest import ApiException

from kagent.tools.cert_manager.tools import (
    CheckCertificateExpiry,
    GetCertificate,
    GetCertificateSecret,
    GetIssuerStatus,
    ListCertificateRequests,
    ListCertificates,
    ListClusterIssuers,
    ListIssuers,
    TriggerRenewal,
)


@pytest.fixture
def mock_custom_api():
    """Mock Kubernetes CustomObjectsApi."""
    with patch("kagent.tools.cert_manager.tools.client.CustomObjectsApi") as mock:
        yield mock.return_value


@pytest.fixture
def mock_core_api():
    """Mock Kubernetes CoreV1Api."""
    with patch("kagent.tools.cert_manager.tools.client.CoreV1Api") as mock:
        yield mock.return_value


@pytest.fixture
def sample_certificate():
    """Sample certificate resource."""
    return {
        "apiVersion": "cert-manager.io/v1",
        "kind": "Certificate",
        "metadata": {
            "name": "example-cert",
            "namespace": "default",
        },
        "spec": {
            "secretName": "example-tls",
            "commonName": "example.com",
            "dnsNames": ["example.com", "www.example.com"],
            "issuerRef": {
                "name": "letsencrypt-prod",
                "kind": "ClusterIssuer",
            },
        },
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True",
                    "reason": "Ready",
                    "message": "Certificate is up to date and has not expired",
                }
            ],
            "notAfter": "2025-01-01T00:00:00Z",
            "renewalTime": "2024-12-01T00:00:00Z",
        },
    }


@pytest.fixture
def sample_issuer():
    """Sample issuer resource."""
    return {
        "apiVersion": "cert-manager.io/v1",
        "kind": "Issuer",
        "metadata": {
            "name": "ca-issuer",
            "namespace": "default",
        },
        "spec": {
            "ca": {
                "secretName": "ca-key-pair",
            },
        },
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True",
                    "reason": "Ready",
                }
            ],
        },
    }


@pytest.fixture
def sample_cluster_issuer():
    """Sample cluster issuer resource."""
    return {
        "apiVersion": "cert-manager.io/v1",
        "kind": "ClusterIssuer",
        "metadata": {
            "name": "letsencrypt-prod",
        },
        "spec": {
            "acme": {
                "server": "https://acme-v02.api.letsencrypt.org/directory",
                "email": "admin@example.com",
            },
        },
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True",
                    "reason": "ACMEAccountRegistered",
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_list_certificates_all_namespaces(mock_custom_api, sample_certificate):
    """Test listing certificates across all namespaces."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [sample_certificate]
    }

    result = await ListCertificates()

    assert result["success"] is True
    assert result["count"] == 1
    assert len(result["certificates"]) == 1
    cert = result["certificates"][0]
    assert cert["name"] == "example-cert"
    assert cert["namespace"] == "default"
    assert cert["ready"] is True

    mock_custom_api.list_cluster_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_list_certificates_specific_namespace(mock_custom_api, sample_certificate):
    """Test listing certificates in a specific namespace."""
    mock_custom_api.list_namespaced_custom_object.return_value = {
        "items": [sample_certificate]
    }

    result = await ListCertificates(namespace="default")

    assert result["success"] is True
    assert result["count"] == 1

    mock_custom_api.list_namespaced_custom_object.assert_called_once_with(
        group="cert-manager.io",
        version="v1",
        namespace="default",
        plural="certificates",
    )


@pytest.mark.asyncio
async def test_list_certificates_api_error(mock_custom_api):
    """Test handling API errors when listing certificates."""
    mock_custom_api.list_cluster_custom_object.side_effect = ApiException(
        status=403,
        reason="Forbidden",
    )

    result = await ListCertificates()

    assert result["success"] is False
    assert "Forbidden" in result["error"]
    assert result["status_code"] == 403


@pytest.mark.asyncio
async def test_get_certificate_success(mock_custom_api, sample_certificate):
    """Test getting a specific certificate."""
    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await GetCertificate(name="example-cert", namespace="default")

    assert result["success"] is True
    cert = result["certificate"]
    assert cert["name"] == "example-cert"
    assert cert["namespace"] == "default"
    assert cert["common_name"] == "example.com"
    assert cert["secret_name"] == "example-tls"


@pytest.mark.asyncio
async def test_get_certificate_not_found(mock_custom_api):
    """Test getting a non-existent certificate."""
    mock_custom_api.get_namespaced_custom_object.side_effect = ApiException(
        status=404,
        reason="Not Found",
    )

    result = await GetCertificate(name="missing-cert", namespace="default")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_check_certificate_expiry_valid(mock_custom_api, sample_certificate):
    """Test checking expiry of a valid certificate."""
    # Set expiry to 45 days from now
    future_date = datetime.now(timezone.utc) + timedelta(days=45)
    sample_certificate["status"]["notAfter"] = future_date.isoformat()

    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await CheckCertificateExpiry(name="example-cert", namespace="default")

    assert result["success"] is True
    expiry = result["expiry"]
    # Allow for 1 day difference due to timing
    assert expiry["days_until_expiry"] in [44, 45]
    assert expiry["is_expiring_soon"] is False
    assert expiry["warning_message"] is None


@pytest.mark.asyncio
async def test_check_certificate_expiry_soon(mock_custom_api, sample_certificate):
    """Test checking expiry of a certificate expiring soon."""
    # Set expiry to 15 days from now
    future_date = datetime.now(timezone.utc) + timedelta(days=15)
    sample_certificate["status"]["notAfter"] = future_date.isoformat()

    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await CheckCertificateExpiry(
        name="example-cert",
        namespace="default",
        warning_days=30,
    )

    assert result["success"] is True
    expiry = result["expiry"]
    # Allow for 1 day difference due to timing
    assert expiry["days_until_expiry"] in [14, 15]
    assert expiry["is_expiring_soon"] is True
    assert "WARNING" in expiry["warning_message"]


@pytest.mark.asyncio
async def test_check_certificate_expiry_expired(mock_custom_api, sample_certificate):
    """Test checking expiry of an expired certificate."""
    # Set expiry to 10 days ago
    past_date = datetime.now(timezone.utc) - timedelta(days=10)
    sample_certificate["status"]["notAfter"] = past_date.isoformat()

    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await CheckCertificateExpiry(name="example-cert", namespace="default")

    assert result["success"] is True
    expiry = result["expiry"]
    # Allow for 1 day difference due to timing
    assert expiry["days_until_expiry"] in [-11, -10]
    assert expiry["is_expiring_soon"] is True
    assert "CRITICAL" in expiry["warning_message"]
    assert "EXPIRED" in expiry["warning_message"]


@pytest.mark.asyncio
async def test_check_certificate_expiry_no_date(mock_custom_api, sample_certificate):
    """Test checking expiry when no expiry date is available."""
    sample_certificate["status"].pop("notAfter", None)

    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await CheckCertificateExpiry(name="example-cert", namespace="default")

    assert result["success"] is True
    expiry = result["expiry"]
    assert expiry["days_until_expiry"] is None
    assert expiry["is_expiring_soon"] is False
    assert "not been issued" in expiry["warning_message"].lower()


@pytest.mark.asyncio
async def test_list_cluster_issuers(mock_custom_api, sample_cluster_issuer):
    """Test listing cluster issuers."""
    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [sample_cluster_issuer]
    }

    result = await ListClusterIssuers()

    assert result["success"] is True
    assert result["count"] == 1
    issuer = result["cluster_issuers"][0]
    assert issuer["name"] == "letsencrypt-prod"
    assert issuer["kind"] == "ClusterIssuer"
    assert issuer["ready"] is True


@pytest.mark.asyncio
async def test_list_issuers(mock_custom_api, sample_issuer):
    """Test listing issuers in a namespace."""
    mock_custom_api.list_namespaced_custom_object.return_value = {
        "items": [sample_issuer]
    }

    result = await ListIssuers(namespace="default")

    assert result["success"] is True
    assert result["count"] == 1
    issuer = result["issuers"][0]
    assert issuer["name"] == "ca-issuer"
    assert issuer["namespace"] == "default"
    assert issuer["kind"] == "Issuer"


@pytest.mark.asyncio
async def test_get_issuer_status_issuer(mock_custom_api, sample_issuer):
    """Test getting status of an Issuer."""
    mock_custom_api.get_namespaced_custom_object.return_value = sample_issuer

    result = await GetIssuerStatus(
        name="ca-issuer",
        namespace="default",
        kind="Issuer",
    )

    assert result["success"] is True
    issuer = result["issuer"]
    assert issuer["name"] == "ca-issuer"
    assert issuer["ready"] is True


@pytest.mark.asyncio
async def test_get_issuer_status_cluster_issuer(mock_custom_api, sample_cluster_issuer):
    """Test getting status of a ClusterIssuer."""
    mock_custom_api.get_cluster_custom_object.return_value = sample_cluster_issuer

    result = await GetIssuerStatus(
        name="letsencrypt-prod",
        kind="ClusterIssuer",
    )

    assert result["success"] is True
    issuer = result["issuer"]
    assert issuer["name"] == "letsencrypt-prod"
    assert issuer["kind"] == "ClusterIssuer"
    assert issuer["ready"] is True


@pytest.mark.asyncio
async def test_get_issuer_status_no_namespace_for_issuer(mock_custom_api):
    """Test error when namespace is not provided for Issuer."""
    result = await GetIssuerStatus(name="ca-issuer", kind="Issuer")

    assert result["success"] is False
    assert "namespace is required" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_issuer_status_invalid_kind(mock_custom_api):
    """Test error when invalid kind is provided."""
    result = await GetIssuerStatus(
        name="test",
        namespace="default",
        kind="InvalidKind",
    )

    assert result["success"] is False
    assert "invalid kind" in result["error"].lower()


@pytest.mark.asyncio
async def test_trigger_renewal(mock_custom_api):
    """Test triggering certificate renewal."""
    mock_custom_api.patch_namespaced_custom_object.return_value = {}

    result = await TriggerRenewal(name="example-cert", namespace="default")

    assert result["success"] is True
    assert "renewal triggered" in result["message"].lower()

    mock_custom_api.patch_namespaced_custom_object.assert_called_once()
    call_args = mock_custom_api.patch_namespaced_custom_object.call_args
    assert call_args.kwargs["name"] == "example-cert"
    assert call_args.kwargs["namespace"] == "default"


@pytest.mark.asyncio
async def test_trigger_renewal_not_found(mock_custom_api):
    """Test triggering renewal for non-existent certificate."""
    mock_custom_api.patch_namespaced_custom_object.side_effect = ApiException(
        status=404,
        reason="Not Found",
    )

    result = await TriggerRenewal(name="missing-cert", namespace="default")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_list_certificate_requests(mock_custom_api):
    """Test listing certificate requests."""
    cert_request = {
        "metadata": {
            "name": "example-cert-1234",
            "namespace": "default",
        },
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "False",
                    "reason": "Pending",
                }
            ],
        },
    }

    mock_custom_api.list_cluster_custom_object.return_value = {
        "items": [cert_request]
    }

    result = await ListCertificateRequests()

    assert result["success"] is True
    assert result["count"] == 1
    request = result["certificate_requests"][0]
    assert request["name"] == "example-cert-1234"
    assert request["ready"] is False


@pytest.mark.asyncio
async def test_list_certificate_requests_with_namespace(mock_custom_api):
    """Test listing certificate requests in a specific namespace."""
    mock_custom_api.list_namespaced_custom_object.return_value = {"items": []}

    result = await ListCertificateRequests(namespace="default")

    assert result["success"] is True
    mock_custom_api.list_namespaced_custom_object.assert_called_once()


@pytest.mark.asyncio
async def test_get_certificate_secret_exists(
    mock_custom_api,
    mock_core_api,
    sample_certificate,
):
    """Test getting certificate secret when it exists."""
    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    mock_secret = MagicMock()
    mock_secret.type = "kubernetes.io/tls"
    mock_core_api.read_namespaced_secret.return_value = mock_secret

    result = await GetCertificateSecret(name="example-cert", namespace="default")

    assert result["success"] is True
    assert result["secret_name"] == "example-tls"
    assert result["secret_exists"] is True
    assert result["secret_type"] == "kubernetes.io/tls"


@pytest.mark.asyncio
async def test_get_certificate_secret_not_exists(
    mock_custom_api,
    mock_core_api,
    sample_certificate,
):
    """Test getting certificate secret when it doesn't exist."""
    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate
    mock_core_api.read_namespaced_secret.side_effect = ApiException(
        status=404,
        reason="Not Found",
    )

    result = await GetCertificateSecret(name="example-cert", namespace="default")

    assert result["success"] is True
    assert result["secret_name"] == "example-tls"
    assert result["secret_exists"] is False
    assert result["secret_type"] is None


@pytest.mark.asyncio
async def test_get_certificate_secret_no_secret_name(
    mock_custom_api,
    sample_certificate,
):
    """Test getting certificate secret when no secret name is configured."""
    sample_certificate["spec"].pop("secretName")
    mock_custom_api.get_namespaced_custom_object.return_value = sample_certificate

    result = await GetCertificateSecret(name="example-cert", namespace="default")

    assert result["success"] is False
    assert "no secret name" in result["error"].lower()
