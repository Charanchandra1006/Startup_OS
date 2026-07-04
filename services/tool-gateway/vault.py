import os
import json
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("chief.vault")

class LocalVault:
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

vault = LocalVault()
