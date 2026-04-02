# kagent cert-manager Tools

MCP tools for monitoring and managing [cert-manager](https://cert-manager.io/) resources in Kubernetes clusters.

## What is cert-manager?

cert-manager is a native Kubernetes certificate management controller. It can help with issuing certificates from a variety of sources, such as Let's Encrypt, HashiCorp Vault, Venafi, a simple signing key pair, or self-signed. It ensures certificates are valid and up-to-date, and attempts to renew certificates at a configured time before expiry.

## Prerequisites

- **cert-manager must be installed** in your Kubernetes cluster. Follow the [official installation guide](https://cert-manager.io/docs/installation/).
- The kagent agent must have appropriate RBAC permissions to read cert-manager CRDs (Certificates, Issuers, ClusterIssuers, CertificateRequests).

## Available Tools

### ListCertificates

List all Certificate resources across namespaces or in a specific namespace.

**Input:**
```python
{
    "namespace": "default"  # Optional - if not provided, lists across all namespaces
}
```

**Output:**
```python
{
    "success": True,
    "count": 2,
    "certificates": [
        {
            "name": "example-cert",
            "namespace": "default",
            "common_name": "example.com",
            "dns_names": ["example.com", "www.example.com"],
            "issuer_name": "letsencrypt-prod",
            "issuer_kind": "ClusterIssuer",
            "secret_name": "example-tls",
            "ready": True,
            "renewal_time": "2024-12-01T00:00:00Z",
            "not_after": "2025-01-01T00:00:00Z",
            "conditions": [...]
        }
    ]
}
```

### GetCertificate

Get details and status of a specific Certificate.

**Input:**
```python
{
    "name": "example-cert",
    "namespace": "default"
}
```

**Output:**
```python
{
    "success": True,
    "certificate": {
        "name": "example-cert",
        "namespace": "default",
        "common_name": "example.com",
        "ready": True,
        ...
    }
}
```

### CheckCertificateExpiry

Return days until certificate expiry and flag if expiring soon.

**Input:**
```python
{
    "name": "example-cert",
    "namespace": "default",
    "warning_days": 30  # Optional - default is 30 days
}
```

**Output:**
```python
{
    "success": True,
    "expiry": {
        "name": "example-cert",
        "namespace": "default",
        "days_until_expiry": 45,
        "expiry_date": "2025-01-01T00:00:00Z",
        "is_expiring_soon": False,
        "warning_message": None  # or "WARNING: Certificate will expire in 15 days"
    }
}
```

### ListClusterIssuers

List all ClusterIssuer resources and their status.

**Input:** None

**Output:**
```python
{
    "success": True,
    "count": 1,
    "cluster_issuers": [
        {
            "name": "letsencrypt-prod",
            "namespace": None,
            "kind": "ClusterIssuer",
            "ready": True,
            "conditions": [...]
        }
    ]
}
```

### ListIssuers

List Issuers in a given namespace.

**Input:**
```python
{
    "namespace": "default"
}
```

**Output:**
```python
{
    "success": True,
    "count": 1,
    "issuers": [
        {
            "name": "ca-issuer",
            "namespace": "default",
            "kind": "Issuer",
            "ready": True,
            "conditions": [...]
        }
    ]
}
```

### GetIssuerStatus

Check if an Issuer or ClusterIssuer is Ready.

**Input:**
```python
{
    "name": "ca-issuer",
    "namespace": "default",  # Required for kind='Issuer', ignored for 'ClusterIssuer'
    "kind": "Issuer"  # Optional - default is 'Issuer', can be 'ClusterIssuer'
}
```

**Output:**
```python
{
    "success": True,
    "issuer": {
        "name": "ca-issuer",
        "namespace": "default",
        "kind": "Issuer",
        "ready": True,
        "conditions": [...]
    }
}
```

### TriggerRenewal

Annotate a Certificate to force renewal.

**Input:**
```python
{
    "name": "example-cert",
    "namespace": "default"
}
```

**Output:**
```python
{
    "success": True,
    "message": "Renewal triggered for certificate 'example-cert' in namespace 'default'"
}
```

### ListCertificateRequests

List pending or failed CertificateRequests.

**Input:**
```python
{
    "namespace": "default"  # Optional - if not provided, lists across all namespaces
}
```

**Output:**
```python
{
    "success": True,
    "count": 1,
    "certificate_requests": [
        {
            "name": "example-cert-1234",
            "namespace": "default",
            "ready": False,
            "failed": False,
            "conditions": [...]
        }
    ]
}
```

### GetCertificateSecret

Retrieve the TLS secret name bound to a Certificate.

**Input:**
```python
{
    "name": "example-cert",
    "namespace": "default"
}
```

**Output:**
```python
{
    "success": True,
    "secret_name": "example-tls",
    "namespace": "default",
    "secret_exists": True,
    "secret_type": "kubernetes.io/tls"
}
```

## How to Add to a kagent Agent

Create an Agent resource that uses these cert-manager tools:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: cert-manager-agent
  namespace: kagent
spec:
  description: Certificate management expert that monitors TLS certificates
  instruction: |
    You are a certificate management expert. You monitor TLS certificate
    health across the cluster, warn about expiring certificates,
    troubleshoot issuer problems, and trigger renewals when needed.

    When a user asks about certificates:
    - Use ListCertificates to get an overview
    - Use CheckCertificateExpiry to identify expiring certificates
    - Use GetIssuerStatus to check if issuers are healthy
    - Use TriggerRenewal when certificates need immediate renewal
  tools:
    - name: cert-manager-tools
      type: MCP
      mcp:
        server: cert-manager-mcp-server
  modelConfig:
    name: default-model
```

Create a ToolServer resource for the cert-manager MCP server:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: ToolServer
metadata:
  name: cert-manager-mcp-server
  namespace: kagent
spec:
  type: MCP
  mcp:
    deployment:
      image: your-registry/kagent-tools-cert-manager:latest
      env:
        - name: KUBERNETES_SERVICE_HOST
          value: "kubernetes.default.svc"
```

## Error Handling

All tools return a consistent error format:

```python
{
    "success": False,
    "error": "Description of what went wrong",
    "status_code": 404  # Optional - HTTP status code from Kubernetes API
}
```

Common error scenarios:
- **404 Not Found**: Resource doesn't exist
- **403 Forbidden**: Insufficient RBAC permissions
- **Connection errors**: Cannot reach Kubernetes API

## Development

### Running Tests

```bash
cd python
uv run pytest ./packages/kagent-tools-cert-manager/tests/
```

### Adding New Tools

1. Add the function to `src/kagent/tools/cert_manager/tools.py`
2. Export it in `src/kagent/tools/cert_manager/__init__.py`
3. Add tests to `tests/test_tools.py`
4. Update this README with usage examples

## License

Apache 2.0 - See LICENSE file in the root of the repository.
