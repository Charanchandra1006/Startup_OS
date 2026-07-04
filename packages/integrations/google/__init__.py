import os
import datetime
from typing import Any
from google.oauth2.credentials import Credentials

from .calendar import read_events, create_event
from .gmail import read_emails, draft_email, send_email

class GoogleIntegrationAdapter:
    def __init__(self, vault_store):
        self.provider = "google"
        self._call_log = []
        self.vault = vault_store

    def _get_credentials(self, tenant_id: str) -> Credentials:
        creds_data = self.vault.get_credential_by_tenant("google", tenant_id)
        if not creds_data:
            raise ValueError(f"Google Credentials not found in vault for tenant {tenant_id}")
        
        return Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            scopes=creds_data.get('scopes')
        )

    def execute_read(self, operation: str, params: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        creds = self._get_credentials(tenant_id)
        
        self._call_log.append({
            "provider": self.provider,
            "operation": operation,
            "params": params,
            "tenant_id": tenant_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": "read",
        })
        
        if operation == "list_events":
            return read_events(creds)
        elif operation == "list_emails":
            return read_emails(creds)
            
        return {"error": f"Unknown read operation {operation}"}
        
    def execute_write(self, operation: str, payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        creds = self._get_credentials(tenant_id)
        
        self._call_log.append({
            "provider": self.provider,
            "operation": operation,
            "payload": payload,
            "tenant_id": tenant_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": "write",
        })
        
        if operation == "create_event":
            return create_event(
                creds, 
                payload.get('summary', 'Meeting'), 
                payload.get('start_time'), 
                payload.get('end_time'), 
                payload.get('attendees')
            )
        elif operation == "draft_email":
            return draft_email(creds, payload.get('to'), payload.get('subject'), payload.get('body'))
        elif operation == "send_email":
            return send_email(creds, payload.get('to'), payload.get('subject'), payload.get('body'))
            
        return {"error": f"Unknown write operation {operation}"}
        
    def get_call_log(self):
        return self._call_log
