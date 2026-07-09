"""
Chief AI Startup OS — Google OAuth Authentication
Implements: Phase 1 Google SSO, Calendar & Gmail scope acquisition

Handles:
1. OAuth flow creation (no PKCE — we use client_secret as a confidential web app)
2. Token exchange
3. User profile fetch
4. Neon DB upsert
5. Vault credential storage
6. JWT issuance
"""

import os
import jwt
import datetime
import logging
import asyncpg
import requests
from urllib.parse import urlencode

logger = logging.getLogger("chief.google_auth")

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for localhost dev

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8002/auth/google/callback")

def build_authorization_url(state: str) -> str:
    """Build the Google OAuth consent screen URL. No PKCE needed for confidential web apps."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID not configured in .env")

    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange the authorization code for access + refresh tokens using client_secret (no PKCE)."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("Google Client ID and Secret are not configured in .env")

    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code",
    }
    
    resp = requests.post(GOOGLE_TOKEN_URL, data=data)
    if resp.status_code != 200:
        logger.error(f"Token exchange failed: {resp.status_code} {resp.text}")
        raise ValueError(f"Google token exchange failed: {resp.json().get('error_description', resp.text)}")
    
    return resp.json()


def fetch_user_profile(access_token: str) -> dict:
    """Fetch the authenticated user's Google profile."""
    resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if resp.status_code != 200:
        raise ValueError(f"Failed to fetch user profile: {resp.text}")
    return resp.json()


async def handle_google_callback(state: str, code: str, vault_store_fn):
    """
    Full Google OAuth callback handler:
    1. Exchange code for tokens (using client_secret, no PKCE)
    2. Fetch user profile from Google
    3. Upsert user in Neon DB
    4. Store credentials in vault
    5. Store integration mapping in DB
    6. Generate and return a JWT
    """
    tenant_id = state  # We passed tenant_id as state

    # Step 1: Exchange code for tokens
    token_data = exchange_code_for_tokens(code)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    
    creds_dict = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': token_data.get('token_type'),
        'expires_in': token_data.get('expires_in'),
        'scope': token_data.get('scope'),
    }

    # Step 2: Fetch user profile
    user_info = fetch_user_profile(access_token)
    email = user_info.get('email')
    name = user_info.get('name')
    picture = user_info.get('picture')
    google_id = user_info.get('id')
    
    logger.info(f"Google OAuth callback for: {email} (tenant: {tenant_id})")

    # Step 3: Connect to Neon DB
    db_url = os.environ.get("DATABASE_URL", "")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in db_url:
        db_url = db_url.split("?")[0]

    conn = await asyncpg.connect(db_url)

    try:
        # Step 4: Upsert user
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        if user_id:
            await conn.execute(
                "UPDATE users SET name = $1, auth_provider_ref = $2 WHERE id = $3",
                name, google_id, user_id
            )
        else:
            import uuid
            user_id = await conn.fetchval(
                """
                INSERT INTO users (tenant_id, email, name, role, auth_provider_ref)
                VALUES ($1::uuid, $2, $3, 'founder', $4)
                RETURNING id
                """,
                uuid.UUID(tenant_id), email, name, google_id
            )

        # Step 5: Store credentials in vault
        vault_ref = vault_store_fn("google", tenant_id, creds_dict)

        # Step 6: Store integration mapping in DB
        try:
            exists = await conn.fetchval(
                "SELECT id FROM integrations WHERE tenant_id = $1::uuid AND provider = 'google'",
                uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
            )
            if exists:
                await conn.execute(
                    "UPDATE integrations SET credential_vault_ref = $1, status = 'active', updated_at = NOW() WHERE id = $2",
                    vault_ref, exists
                )
            else:
                await conn.execute(
                    "INSERT INTO integrations (tenant_id, provider, category, credential_vault_ref, status) VALUES ($1::uuid, 'google', 'productivity', $2, 'active')",
                    uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id, vault_ref
                )
        except Exception as e:
            logger.warning(f"Could not update integrations table (may not exist yet): {e}")

        # Step 7: Generate JWT
        jwt_secret = os.environ.get("JWT_SECRET", "changeme_jwt_secret")
        jwt_issuer = os.environ.get("JWT_ISSUER", "chief-dev")

        token = jwt.encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "role": "founder",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                "iss": jwt_issuer
            },
            jwt_secret,
            algorithm="HS256"
        )

        return {
            "token": token,
            "user": {
                "id": str(user_id),
                "name": name,
                "email": email,
                "avatar_url": picture
            }
        }
    finally:
        await conn.close()
