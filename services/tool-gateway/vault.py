"""
Chief AI Startup OS — Multi-Backend Credential Vault
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 4.1-4.3 / SPEC-GAPS SG-001

Three backends:
- LocalVault: File-backed JSON (dev only)
- AWSSecretsManagerVault: AWS Secrets Manager (production)
- VaultFactory: Selects backend based on VAULT_BACKEND env var

The vault contract:
- store_credential(provider, tenant_id, payload) → vault_ref UUID
- get_credential(vault_ref) → payload dict
- get_credential_by_tenant(provider, tenant_id) → payload dict
- update_credential(vault_ref, payload) → None

Operational databases NEVER store credentials directly — only vault_ref UUIDs.
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger("chief.vault")


# ─── Vault Interface ─────────────────────────────────────────────────────────

class VaultBackend(ABC):
    """Abstract vault backend. All backends implement the same 4-method contract."""

    @abstractmethod
    def store_credential(self, provider: str, tenant_id: str, payload: dict) -> str:
        """Store a credential and return a vault reference UUID."""

    @abstractmethod
    def update_credential(self, vault_ref: str, payload: dict) -> None:
        """Update an existing credential payload."""

    @abstractmethod
    def get_credential(self, vault_ref: str) -> Optional[dict]:
        """Retrieve a credential by its vault reference UUID."""

    @abstractmethod
    def get_credential_by_tenant(self, provider: str, tenant_id: str) -> Optional[dict]:
        """Retrieve a credential by tenant and provider."""


# ─── Local Vault (Dev Only) ──────────────────────────────────────────────────

class LocalVault(VaultBackend):
    """
    A simple file-backed credential vault for Phase 1 development.
    Satisfies the requirement that operational databases NEVER store credentials directly.
    """
    def __init__(self, storage_file: str = "d:\\Startup_OS\\.vault.json"):
        self.storage_file = storage_file
        self.credentials: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load vault: {e}")
        return {}

    def _save(self) -> None:
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.credentials, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")

    def store_credential(self, provider: str, tenant_id: str, payload: dict) -> str:
        """Store a credential and return a vault reference UUID."""
        vault_ref = str(uuid.uuid4())
        self.credentials[vault_ref] = {
            "provider": provider,
            "tenant_id": tenant_id,
            "payload": payload
        }
        self._save()
        return vault_ref
        
    def update_credential(self, vault_ref: str, payload: dict) -> None:
        """Update an existing credential."""
        if vault_ref in self.credentials:
            self.credentials[vault_ref]["payload"].update(payload)
            self._save()
            
    def get_credential(self, vault_ref: str) -> Optional[dict]:
        """Retrieve a credential by its reference."""
        record = self.credentials.get(vault_ref)
        if record:
            return record["payload"]
        return None
        
    def get_credential_by_tenant(self, provider: str, tenant_id: str) -> Optional[dict]:
        """Retrieve a credential by tenant and provider (useful for dev/Phase 1)."""
        for ref, record in self.credentials.items():
            if record["provider"] == provider and record["tenant_id"] == tenant_id:
                return record["payload"]
        return None


# ─── AWS Secrets Manager Vault (Production) ──────────────────────────────────

class AWSSecretsManagerVault(VaultBackend):
    """
    Production vault backend using AWS Secrets Manager.
    
    Secret naming convention: chief/{tenant_id}/{provider}
    Each secret value is a JSON string containing the credential payload.
    A local index maps vault_ref UUIDs to secret names for backward compat.
    
    Requires: boto3, AWS credentials (IAM role in EKS, or env vars for dev).
    """

    def __init__(self, region: str = "us-east-1"):
        try:
            import boto3
            self._client = boto3.client("secretsmanager", region_name=region)
            self._region = region
            logger.info(f"AWS Secrets Manager vault initialized (region={region})")
        except ImportError:
            raise ImportError(
                "boto3 is required for AWS Secrets Manager vault. "
                "Install with: pip install boto3"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AWS Secrets Manager client: {e}")

        # Local in-memory index: vault_ref → (provider, tenant_id)
        self._ref_index: Dict[str, tuple[str, str]] = {}

    def _secret_name(self, provider: str, tenant_id: str) -> str:
        """Construct the AWS secret name for a given provider + tenant."""
        return f"chief/{tenant_id}/{provider}"

    def store_credential(self, provider: str, tenant_id: str, payload: dict) -> str:
        vault_ref = str(uuid.uuid4())
        secret_name = self._secret_name(provider, tenant_id)

        try:
            # Try to create the secret
            self._client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(payload),
                Description=f"Chief OS credential for {provider} (tenant {tenant_id})",
                Tags=[
                    {"Key": "tenant_id", "Value": tenant_id},
                    {"Key": "provider", "Value": provider},
                    {"Key": "vault_ref", "Value": vault_ref},
                ],
            )
        except self._client.exceptions.ResourceExistsException:
            # Secret already exists — update it
            self._client.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(payload),
            )

        self._ref_index[vault_ref] = (provider, tenant_id)
        logger.info(f"Stored credential in AWS: {secret_name}")
        return vault_ref

    def update_credential(self, vault_ref: str, payload: dict) -> None:
        if vault_ref not in self._ref_index:
            logger.warning(f"Unknown vault_ref {vault_ref} — cannot update in AWS")
            return

        provider, tenant_id = self._ref_index[vault_ref]
        secret_name = self._secret_name(provider, tenant_id)

        try:
            existing = self._client.get_secret_value(SecretId=secret_name)
            current = json.loads(existing["SecretString"])
            current.update(payload)
            self._client.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(current),
            )
        except Exception as e:
            logger.error(f"Failed to update AWS secret {secret_name}: {e}")

    def get_credential(self, vault_ref: str) -> Optional[dict]:
        if vault_ref not in self._ref_index:
            return None

        provider, tenant_id = self._ref_index[vault_ref]
        return self.get_credential_by_tenant(provider, tenant_id)

    def get_credential_by_tenant(self, provider: str, tenant_id: str) -> Optional[dict]:
        secret_name = self._secret_name(provider, tenant_id)
        try:
            response = self._client.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except self._client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve AWS secret {secret_name}: {e}")
            return None


# ─── Vault Factory ────────────────────────────────────────────────────────────

def _create_vault() -> VaultBackend:
    """Select vault backend based on VAULT_BACKEND environment variable.
    
    Supported values:
    - 'local' (default): File-backed JSON vault for development
    - 'aws': AWS Secrets Manager
    """
    backend = os.environ.get("VAULT_BACKEND", "local").lower()

    if backend == "aws":
        region = os.environ.get("AWS_REGION", "us-east-1")
        logger.info(f"Initializing AWS Secrets Manager vault (region={region})")
        return AWSSecretsManagerVault(region=region)
    elif backend == "local":
        logger.info("Initializing local file-backed vault")
        return LocalVault()
    else:
        logger.warning(
            f"Unknown VAULT_BACKEND '{backend}', falling back to local vault"
        )
        return LocalVault()


# Module-level singleton — all consumers import this
vault = _create_vault()
