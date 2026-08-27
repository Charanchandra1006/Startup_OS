"""
Chief AI Startup OS — Google OAuth Authentication
Implements: Incremental Authorization (privacy-friendly progressive scope requests)

Flow:
1. Initial login: only openid + email + profile
2. When agent needs Calendar/Gmail/Drive/Sheets → request that specific scope incrementally
3. Token exchange + refresh token stored in Vault
4. Agents use stored tokens; auto-refresh handles expiry
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

# ─── Scope Definitions ────────────────────────────────────────────────────────
# Only basic scopes at first login. Additional scopes are requested incrementally.

BASIC_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# Scopes that can be requested incrementally when an agent needs them
INCREMENTAL_SCOPES = {
    'gmail': [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
    ],
    'calendar': [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar',
    ],
    'drive.readonly': [
        'https://www.googleapis.com/auth/drive.readonly',
    ],
    'drive.file': [
        'https://www.googleapis.com/auth/drive.file',
    ],
    'drive.full': [
        'https://www.googleapis.com/auth/drive',
    ],
    'sheets': [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
    ],
}

# For backwards compatibility / dev convenience: all scopes combined
ALL_SCOPES = BASIC_SCOPES + [s for group in INCREMENTAL_SCOPES.values() for s in group]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8002/auth/google/callback")

def build_authorization_url(state: str, scopes: list[str] | None = None) -> str:
    """Build the Google OAuth consent screen URL.
    
    Args:
        state: Opaque state string (we pass tenant_id)
        scopes: Which scopes to request. Defaults to BASIC_SCOPES for first login.
                 For incremental auth, pass the additional scopes needed.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID not configured in .env")

    requested_scopes = scopes or BASIC_SCOPES

    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(requested_scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",  # This enables incremental authorization
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def build_incremental_auth_url(state: str, service: str) -> str:
    """Build an incremental authorization URL for a specific Google service.
    
    Args:
        state: Opaque state (tenant_id)  
        service: One of 'gmail', 'calendar', 'drive', 'sheets'
    
    Returns:
        Authorization URL that requests only the additional scopes needed.
    """
    additional_scopes = INCREMENTAL_SCOPES.get(service)
    if not additional_scopes:
        raise ValueError(f"Unknown service '{service}'. Valid: {list(INCREMENTAL_SCOPES.keys())}")
    
    # include_granted_scopes=true tells Google to merge with existing grants
    return build_authorization_url(state, scopes=additional_scopes)


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


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token without user interaction."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    
    resp = requests.post(GOOGLE_TOKEN_URL, data=data)
    if resp.status_code != 200:
        logger.error(f"Token refresh failed: {resp.status_code} {resp.text}")
        raise ValueError(f"Token refresh failed: {resp.text}")
    
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


def get_granted_scopes(access_token: str) -> list[str]:
    """Check which scopes have been granted for this token."""
    resp = requests.get(
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
    )
    if resp.status_code == 200:
        scope_str = resp.json().get("scope", "")
        return scope_str.split(" ") if scope_str else []
    return []


def check_scope_granted(access_token: str, service: str) -> bool:
    """Check if a specific service's scopes have been granted."""
    required = INCREMENTAL_SCOPES.get(service, [])
    if not required:
        return False
    granted = get_granted_scopes(access_token)
    return all(s in granted for s in required)


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

    # Step 3: Connect to Neon DB (with robust fallback for offline/paused databases)
    db_url = os.environ.get("DATABASE_URL", "").strip()
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in db_url:
        db_url = db_url.split("?")[0]
    
    conn = None
    user_id = None
    try:
        # Neon DB requires SSL, use native string parameter
        conn = await asyncpg.connect(db_url, ssl='require', timeout=5.0)
        
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
            
        # Store integration mapping in DB
        vault_ref = vault_store_fn("google", tenant_id, creds_dict)
        try:
            exists = await conn.fetchval(
                "SELECT id FROM integrations WHERE tenant_id = $1::uuid AND provider = 'google'",
                uuid.UUID(tenant_id)
            )
            if exists:
                await conn.execute(
                    "UPDATE integrations SET credential_vault_ref = $1, status = 'active', updated_at = NOW() WHERE id = $2",
                    vault_ref, exists
                )
            else:
                await conn.execute(
                    "INSERT INTO integrations (tenant_id, provider, category, credential_vault_ref, status) VALUES ($1::uuid, 'google', 'productivity', $2, 'active')",
                    uuid.UUID(tenant_id), vault_ref
                )
        except Exception as e:
            logger.warning(f"Could not update integrations table: {e}")
            
    except Exception as e:
        logger.error(f"Database unavailable, using fallback for OAuth completion: {e}")
        import uuid
        user_id = uuid.uuid4()
        # Still store in vault so gateway works
        vault_store_fn("google", tenant_id, creds_dict)
    finally:
        if conn:
            await conn.close()

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
