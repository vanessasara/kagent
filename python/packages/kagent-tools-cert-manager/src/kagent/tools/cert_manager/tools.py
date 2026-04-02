"""cert-manager MCP tools implementation."""

import logging
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser
from kubernetes import client
from kubernetes.client.rest import ApiException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CertificateInfo(BaseModel):
    """Information about a Certificate resource."""

    name: str
    namespace: str
    common_name: str | None = None
    dns_names: list[str] = Field(default_factory=list)
    issuer_name: str | None = None
    issuer_kind: str | None = None
    secret_name: str | None = None
    ready: bool = False
    renewal_time: str | None = None
    not_after: str | None = None
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class IssuerInfo(BaseModel):
    """Information about an Issuer or ClusterIssuer."""

    name: str
    namespace: str | None = None
    kind: str
    ready: bool = False
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class CertificateRequestInfo(BaseModel):
    """Information about a CertificateRequest."""

    name: str
    namespace: str
    ready: bool = False
    failed: bool = False
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class ExpiryInfo(BaseModel):
    """Certificate expiry information."""

    name: str
    namespace: str
    days_until_expiry: int | None = None
    expiry_date: str | None = None
    is_expiring_soon: bool = False
    warning_message: str | None = None


async def ListCertificates(namespace: str | None = None) -> dict[str, Any]:
    """List all Certificate resources across namespaces or in a specific namespace.

    Args:
        namespace: Optional namespace to filter certificates. If None, lists across all namespaces.

    Returns:
        Dictionary containing list of certificates and count.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificates"

        if namespace:
            response = custom_api.list_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
            )
        else:
            response = custom_api.list_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
            )

        certificates = []
        for item in response.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            cert_info = CertificateInfo(
                name=metadata.get("name", ""),
                namespace=metadata.get("namespace", ""),
                common_name=spec.get("commonName"),
                dns_names=spec.get("dnsNames", []),
                issuer_name=spec.get("issuerRef", {}).get("name"),
                issuer_kind=spec.get("issuerRef", {}).get("kind"),
                secret_name=spec.get("secretName"),
                ready=_is_ready(status.get("conditions", [])),
                renewal_time=status.get("renewalTime"),
                not_after=status.get("notAfter"),
                conditions=status.get("conditions", []),
            )
            certificates.append(cert_info.model_dump())

        return {
            "success": True,
            "certificates": certificates,
            "count": len(certificates),
        }

    except ApiException as e:
        logger.error(f"Kubernetes API error listing certificates: {e}")
        return {
            "success": False,
            "error": f"Failed to list certificates: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error listing certificates: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def GetCertificate(name: str, namespace: str) -> dict[str, Any]:
    """Get details and status of a specific Certificate.

    Args:
        name: Name of the Certificate resource.
        namespace: Namespace of the Certificate resource.

    Returns:
        Dictionary containing certificate details.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificates"

        response = custom_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )

        metadata = response.get("metadata", {})
        spec = response.get("spec", {})
        status = response.get("status", {})

        cert_info = CertificateInfo(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            common_name=spec.get("commonName"),
            dns_names=spec.get("dnsNames", []),
            issuer_name=spec.get("issuerRef", {}).get("name"),
            issuer_kind=spec.get("issuerRef", {}).get("kind"),
            secret_name=spec.get("secretName"),
            ready=_is_ready(status.get("conditions", [])),
            renewal_time=status.get("renewalTime"),
            not_after=status.get("notAfter"),
            conditions=status.get("conditions", []),
        )

        return {
            "success": True,
            "certificate": cert_info.model_dump(),
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Certificate '{name}' not found in namespace '{namespace}'",
            }
        logger.error(f"Kubernetes API error getting certificate: {e}")
        return {
            "success": False,
            "error": f"Failed to get certificate: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error getting certificate: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def CheckCertificateExpiry(name: str, namespace: str, warning_days: int = 30) -> dict[str, Any]:
    """Return days until certificate expiry and flag if expiring soon.

    Args:
        name: Name of the Certificate resource.
        namespace: Namespace of the Certificate resource.
        warning_days: Number of days before expiry to flag as expiring soon (default: 30).

    Returns:
        Dictionary containing expiry information.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificates"

        response = custom_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )

        status = response.get("status", {})
        not_after = status.get("notAfter")

        if not not_after:
            return {
                "success": True,
                "expiry": {
                    "name": name,
                    "namespace": namespace,
                    "days_until_expiry": None,
                    "expiry_date": None,
                    "is_expiring_soon": False,
                    "warning_message": "Certificate has not been issued yet or expiry date is not available",
                },
            }

        # Parse the expiry date
        expiry_date = date_parser.parse(not_after)
        now = datetime.now(timezone.utc)
        days_until_expiry = (expiry_date - now).days

        is_expiring_soon = days_until_expiry <= warning_days
        warning_message = None

        if days_until_expiry < 0:
            warning_message = f"CRITICAL: Certificate has EXPIRED {abs(days_until_expiry)} days ago!"
        elif is_expiring_soon:
            warning_message = f"WARNING: Certificate will expire in {days_until_expiry} days"

        expiry_info = ExpiryInfo(
            name=name,
            namespace=namespace,
            days_until_expiry=days_until_expiry,
            expiry_date=not_after,
            is_expiring_soon=is_expiring_soon,
            warning_message=warning_message,
        )

        return {
            "success": True,
            "expiry": expiry_info.model_dump(),
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Certificate '{name}' not found in namespace '{namespace}'",
            }
        logger.error(f"Kubernetes API error checking certificate expiry: {e}")
        return {
            "success": False,
            "error": f"Failed to check certificate expiry: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error checking certificate expiry: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def ListClusterIssuers() -> dict[str, Any]:
    """List all ClusterIssuer resources and their status.

    Returns:
        Dictionary containing list of ClusterIssuers and count.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "clusterissuers"

        response = custom_api.list_cluster_custom_object(
            group=group,
            version=version,
            plural=plural,
        )

        issuers = []
        for item in response.get("items", []):
            metadata = item.get("metadata", {})
            status = item.get("status", {})

            issuer_info = IssuerInfo(
                name=metadata.get("name", ""),
                namespace=None,
                kind="ClusterIssuer",
                ready=_is_ready(status.get("conditions", [])),
                conditions=status.get("conditions", []),
            )
            issuers.append(issuer_info.model_dump())

        return {
            "success": True,
            "cluster_issuers": issuers,
            "count": len(issuers),
        }

    except ApiException as e:
        logger.error(f"Kubernetes API error listing ClusterIssuers: {e}")
        return {
            "success": False,
            "error": f"Failed to list ClusterIssuers: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error listing ClusterIssuers: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def ListIssuers(namespace: str) -> dict[str, Any]:
    """List Issuers in a given namespace.

    Args:
        namespace: Namespace to list Issuers from.

    Returns:
        Dictionary containing list of Issuers and count.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "issuers"

        response = custom_api.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
        )

        issuers = []
        for item in response.get("items", []):
            metadata = item.get("metadata", {})
            status = item.get("status", {})

            issuer_info = IssuerInfo(
                name=metadata.get("name", ""),
                namespace=metadata.get("namespace", ""),
                kind="Issuer",
                ready=_is_ready(status.get("conditions", [])),
                conditions=status.get("conditions", []),
            )
            issuers.append(issuer_info.model_dump())

        return {
            "success": True,
            "issuers": issuers,
            "count": len(issuers),
        }

    except ApiException as e:
        logger.error(f"Kubernetes API error listing Issuers: {e}")
        return {
            "success": False,
            "error": f"Failed to list Issuers: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error listing Issuers: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def GetIssuerStatus(name: str, namespace: str | None = None, kind: str = "Issuer") -> dict[str, Any]:
    """Check if an Issuer or ClusterIssuer is Ready.

    Args:
        name: Name of the Issuer or ClusterIssuer.
        namespace: Namespace of the Issuer (required for kind='Issuer', ignored for ClusterIssuer).
        kind: Kind of issuer - 'Issuer' or 'ClusterIssuer' (default: 'Issuer').

    Returns:
        Dictionary containing issuer status.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"

        if kind == "ClusterIssuer":
            plural = "clusterissuers"
            response = custom_api.get_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                name=name,
            )
        elif kind == "Issuer":
            if not namespace:
                return {
                    "success": False,
                    "error": "Namespace is required for Issuer kind",
                }
            plural = "issuers"
            response = custom_api.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=name,
            )
        else:
            return {
                "success": False,
                "error": f"Invalid kind '{kind}'. Must be 'Issuer' or 'ClusterIssuer'",
            }

        metadata = response.get("metadata", {})
        status = response.get("status", {})

        issuer_info = IssuerInfo(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace") if kind == "Issuer" else None,
            kind=kind,
            ready=_is_ready(status.get("conditions", [])),
            conditions=status.get("conditions", []),
        )

        return {
            "success": True,
            "issuer": issuer_info.model_dump(),
        }

    except ApiException as e:
        if e.status == 404:
            location = f"namespace '{namespace}'" if kind == "Issuer" else "cluster"
            return {
                "success": False,
                "error": f"{kind} '{name}' not found in {location}",
            }
        logger.error(f"Kubernetes API error getting issuer status: {e}")
        return {
            "success": False,
            "error": f"Failed to get issuer status: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error getting issuer status: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def TriggerRenewal(name: str, namespace: str) -> dict[str, Any]:
    """Annotate a Certificate to force renewal.

    Args:
        name: Name of the Certificate to renew.
        namespace: Namespace of the Certificate.

    Returns:
        Dictionary indicating success or failure.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificates"

        # Add annotation to trigger renewal
        patch = {
            "metadata": {
                "annotations": {
                    "cert-manager.io/issue-temporary-certificate": "true",
                }
            }
        }

        custom_api.patch_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
            body=patch,
        )

        return {
            "success": True,
            "message": f"Renewal triggered for certificate '{name}' in namespace '{namespace}'",
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Certificate '{name}' not found in namespace '{namespace}'",
            }
        logger.error(f"Kubernetes API error triggering renewal: {e}")
        return {
            "success": False,
            "error": f"Failed to trigger renewal: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error triggering renewal: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def ListCertificateRequests(namespace: str | None = None) -> dict[str, Any]:
    """List pending or failed CertificateRequests.

    Args:
        namespace: Optional namespace to filter requests. If None, lists across all namespaces.

    Returns:
        Dictionary containing list of certificate requests.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificaterequests"

        if namespace:
            response = custom_api.list_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
            )
        else:
            response = custom_api.list_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
            )

        requests = []
        for item in response.get("items", []):
            metadata = item.get("metadata", {})
            status = item.get("status", {})
            conditions = status.get("conditions", [])

            ready = _is_ready(conditions)
            failed = _is_failed(conditions)

            request_info = CertificateRequestInfo(
                name=metadata.get("name", ""),
                namespace=metadata.get("namespace", ""),
                ready=ready,
                failed=failed,
                conditions=conditions,
            )
            requests.append(request_info.model_dump())

        return {
            "success": True,
            "certificate_requests": requests,
            "count": len(requests),
        }

    except ApiException as e:
        logger.error(f"Kubernetes API error listing CertificateRequests: {e}")
        return {
            "success": False,
            "error": f"Failed to list CertificateRequests: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error listing CertificateRequests: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


async def GetCertificateSecret(name: str, namespace: str) -> dict[str, Any]:
    """Retrieve the TLS secret name bound to a Certificate.

    Args:
        name: Name of the Certificate resource.
        namespace: Namespace of the Certificate resource.

    Returns:
        Dictionary containing the secret name.
    """
    try:
        custom_api = client.CustomObjectsApi()
        group = "cert-manager.io"
        version = "v1"
        plural = "certificates"

        response = custom_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )

        spec = response.get("spec", {})
        secret_name = spec.get("secretName")

        if not secret_name:
            return {
                "success": False,
                "error": f"No secret name configured for certificate '{name}'",
            }

        # Try to get the secret to verify it exists
        try:
            v1 = client.CoreV1Api()
            secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
            secret_exists = True
            secret_type = secret.type
        except ApiException as secret_error:
            if secret_error.status == 404:
                secret_exists = False
                secret_type = None
            else:
                raise

        return {
            "success": True,
            "secret_name": secret_name,
            "namespace": namespace,
            "secret_exists": secret_exists,
            "secret_type": secret_type,
        }

    except ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Certificate '{name}' not found in namespace '{namespace}'",
            }
        logger.error(f"Kubernetes API error getting certificate secret: {e}")
        return {
            "success": False,
            "error": f"Failed to get certificate secret: {e.reason}",
            "status_code": e.status,
        }
    except Exception as e:
        logger.error(f"Unexpected error getting certificate secret: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }


def _is_ready(conditions: list[dict[str, Any]]) -> bool:
    """Check if a resource is ready based on its conditions.

    Args:
        conditions: List of condition dictionaries.

    Returns:
        True if the Ready condition is True, False otherwise.
    """
    for condition in conditions:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


def _is_failed(conditions: list[dict[str, Any]]) -> bool:
    """Check if a resource has failed based on its conditions.

    Args:
        conditions: List of condition dictionaries.

    Returns:
        True if any condition indicates failure, False otherwise.
    """
    for condition in conditions:
        if condition.get("type") in ["Failed", "InvalidRequest"]:
            if condition.get("status") == "True":
                return True
    return False
